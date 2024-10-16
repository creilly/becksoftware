/*
 * uno.c
 *
 * Created: 1/3/2023 11:27:39 AM
 * Author : reilly
 */ 

#define F_CPU 16000000UL // clock speed of crystal oscillator integrated into arduino
#define F_FUND 3555.0 // base frequency (in Hz) from which subharmonics are synthesized
#define PRESCALAR1 8 // clock resolution for counter1 (set so that oscillation period of C1 is < 2^16 counts)
#define PRESCALAR0 8 // clock resolution for counter0 (set so that sufficient time passes between interrupts)
#define SUB0A 10 // subharmonic for waveform A of counter0 (e.g. if F_FUND is 1000 Hz and SUB0A is 10, then freq of waveform A of counter0 is 100 Hz)
#define SUB0B 15 // subharmonic for waveform B of counter0
#define SUB1A 12 // subharmonic for waveform A of counter1 (set equal to double of desired subharmonic for motor frequency [in chopper slits / second]
#define SUB1B 60 // subharmonic for waveform B of counter1 (set equal to double of desired subharmonic for motor frequency [in chopper slits / second]
#define C1A 0 // identifier for waveform A of counter1
#define C1B 1 // identifier for waveform B of counter1
#define C0A 2 // identifier for waveform A of counter0
#define C0B 3 // identifier for waveform B of counter0

// phase shift modes
#define SHIFT_IDLE 0
#define SHIFT_REQUESTED 1
#define UNSHIFT_REQUESTED 2

// dac constants
#define DAC0 (1L << 15) // initial dac value (set to midpoint of dynamic range)
#define DACMIN 4096 // lower rail dac output
#define DACMAX 61440 // upper rail dac output

// aliases for DAC communication lines
#define CLK PORTB5
#define DIN PORTB4
#define CS PORTB3

// bitwise operations
#define bor(x, ...) _bor(x, __VA_ARGS__) // bitwise OR w/ arbitrary arguments
#define set(p, ...) p |= bor(__VA_ARGS__, -1) // set bits of register p
#define unset(p, ...) p &= ~(bor(__VA_ARGS__, -1)) // unset bits of register p
#define get_bit(B,b) (((B) >> (b)) & 1) // get bit b of byte B
#define round(x,y) (y)((x) + 0.5) // floating point round of x to data type y

#include <avr/io.h>
#include <avr/interrupt.h>
#include <stdarg.h> // for functions w/ arbitrary num of args
#include <stdint.h> // get aliases of data types which specify size (e.g. uint8_t)
#include <stdbool.h> // for boolean data type alias

// data structure which manages counter/waveform state
typedef struct Counters {
	uint16_t period;
	volatile uint16_t cycles, remainder;
	volatile uint16_t cycle;
	volatile bool state;
	uint8_t oc_reg, state_bit, tc_reg, bytes;
} Counter;

// variable holding current dac value
uint16_t dac;

// counters C1A, C1B, C0A, C0B
Counter counters[4];

// C0A phase shifter vars
volatile uint8_t shift_signal = SHIFT_IDLE;
uint8_t shift_value = 10;
volatile int8_t shift_sign = +1;

// performs bitwise or of ints x, ... until it reaches terminating value (anything < 0)
uint8_t _bor(int x, ...) {
	va_list l;
	uint8_t r = 0;
	int y = x;
	va_start(l, x);
	while (y >= 0) {
		r |= 1 << y;
		y = va_arg(l, int);
	}
	va_end(l);
	return r;
}

// update 1 or 2 byte registers
void set_reg(uint8_t add, volatile uint16_t state, uint8_t bytes) {
	uint8_t substate, byte;
	volatile uint8_t* subadd;
	for (int i = 0; i < bytes; i++) {
		// high byte must be written first!
		byte = bytes - i - 1;
		subadd = add + byte;
		substate = state >> (byte * 8);
		*subadd = substate;
		subadd += 1;
	}
}

// query 1 or 2 byte registers
volatile uint16_t get_reg(uint8_t add, uint8_t bytes) {
	uint16_t result = 0;
	volatile uint8_t* subadd = add;
	for (int i = 0; i < bytes; i++) {
		result |= (uint16_t)(*subadd) << (i * 8);
		subadd += 1;
	}
	return result;
}

// set output compare register
void set_oc(Counter* counter, volatile uint16_t state) {
	set_reg(counter->oc_reg,state,counter->bytes);
}

// get output compare register
volatile uint16_t get_oc(Counter* counter) {
	return get_reg(counter->oc_reg, counter->bytes);
}

// set bit of register to state
void toggle_bit(uint8_t add, uint8_t bit, uint8_t state) {
	volatile uint8_t* reg = add;
	if (state) {
		*reg |= 1 << bit;
	}
	else {
		*reg &= ~(1 << bit);
	}
}

// set counter prescalar
void set_ps(uint8_t add, uint16_t prescalar, uint8_t bit) {
	uint8_t data;
	switch (prescalar)
	{
		case 1:
			data = 1;
			break;
		case 8:
			data = 2;
			break;
		case 64:
			data = 3;
			break;
		case 256:
			data = 4;
			break;
		case 1024:
			data = 5;
			break;
	}
	set_reg(add,data << bit,1);
}

// determine divisor <= max_denominator that produces maximum remainder when dividing numerator
void get_largest_remainder(uint32_t numerator, uint32_t max_denominator, uint16_t* opt_denominator, uint16_t* max_remainder, uint16_t* cycles) {
	*max_remainder = 0;
	uint32_t remainder;
	uint16_t quotient;
	if (max_denominator > numerator) {
		*max_remainder = numerator;
		*opt_denominator = max_denominator;
		*cycles = 0;
		return;
	}
	for(uint32_t denominator = max_denominator; denominator > *max_remainder; --denominator) {
		quotient = numerator / denominator;
		remainder = numerator - quotient * denominator;
		if (remainder > *max_remainder) {
			*max_remainder = remainder;
			*opt_denominator = denominator;
			*cycles = quotient;
		}
	}
}

// initialize timers
void init_timers(void) {
	// disable prescalar
	set(GTCCR,TSM);
		
	// reset prescalar
	set(GTCCR,PSRSYNC);
	
	// get largest prescalar
	uint8_t prescalaro = PRESCALAR0 > PRESCALAR1 ? PRESCALAR0 : PRESCALAR1;
	
	// determine period of base frequency in units of largest prescalar
	uint32_t periodo = round(F_CPU/F_FUND/2/prescalaro,uint32_t);
	
	// preloop variable initializations
	uint32_t period;
	uint16_t subharmonic;
	uint8_t tc_bit, isc1;
	
	// compute counter properties
	for (int i = 0; i < 4; i++) {
		isc1 = i == C1A || i == C1B;
		uint16_t prescalar = isc1 ? PRESCALAR1 : PRESCALAR0;
		Counter* counter = counters + i;
		counter->bytes = isc1 ? 2 : 1;
		counter->state = false;
		counter->tc_reg = isc1 ? &TCCR1A : &TCCR0A;
		set_ps(isc1 ? &TCCR1B : &TCCR0B, prescalar, isc1 ? CS10 : CS00);
		switch (i) {
			case C1A:
				subharmonic = SUB1A;
				counter->oc_reg = &OCR1A;
				counter->state_bit = COM1A0;
				tc_bit = COM1A1;
				break;
			case C1B:
				subharmonic = SUB1B;
				counter->oc_reg = &OCR1B;
				counter->state_bit = COM1B0;
				tc_bit = COM1B1;
				break;
			case C0A:
				subharmonic = SUB0A;
				counter->oc_reg = &OCR0A;
				counter->state_bit = COM0A0;
				tc_bit = COM0A1;
				break;
			case C0B:
				subharmonic = SUB0B;
				counter->oc_reg = &OCR0B;
				counter->state_bit = COM0B0;
				tc_bit = COM0B1;
				break;		
		}
		// set counters to run
		toggle_bit(counter->tc_reg,tc_bit,true);
		period = periodo * prescalaro / prescalar * subharmonic;
		get_largest_remainder(period,(1L << (counter->bytes * 8)) - (i == C1A ? shift_value : 0),&counter->period,&counter->remainder,&counter->cycles);
		counter->cycle = counter->cycles;
		set_oc(counter,counter->cycle ? counter->period : counter->remainder);
	}
	
	// set counter0 output compare pins to output
	set(DDRD,DDD6,DDD5);
	
	// set counter1 output compare pins to output
	set(DDRB,DDB1,DDB2);
	
	// enable interrupt for counter0 comp matches
	set(TIMSK0,OCIE0A,OCIE0B);
	
	// enable interrupt for counter1 comp match
	set(TIMSK1,OCIE1A,OCIE1B);
	
	// enable counters
	unset(GTCCR,TSM);
}

// configure counter to change state (TTL level) on next output compare match
void toggle_counter(Counter* counter) {
	toggle_bit(counter->tc_reg,counter->state_bit,counter->state);
	counter->state = !counter->state;
}

// set next output compare value
void increment_oc(Counter* counter, uint16_t delta) {
	set_oc(counter,get_oc(counter) + delta);
}

// handle output compare match
void output_compare_update(uint8_t counter_index) {
	Counter* counter = counters + counter_index;
	uint16_t cycle = counter->cycle--;
	if (cycle == 0) {
		// phase shift logic
		if (counter_index == C1A) {
			if (shift_signal == SHIFT_REQUESTED) {
				counter->remainder += shift_sign * shift_value;
				shift_signal = UNSHIFT_REQUESTED;
			}
			else if (shift_signal == UNSHIFT_REQUESTED) {
				counter->remainder -= shift_sign * shift_value;
				shift_signal = SHIFT_IDLE;
			}
		}
		counter->cycle = counter->cycles;
		if (counter->cycle == 0) {
			toggle_counter(counter);
		}
	}
	else if (cycle == 1) {
		toggle_counter(counter);
	}
	increment_oc(counter,cycle ? counter->period : counter->remainder);
}

ISR(TIMER1_COMPA_vect) {
	output_compare_update(C1A);
}

ISR(TIMER1_COMPB_vect) {
	output_compare_update(C1B);
}

ISR(TIMER0_COMPA_vect) {
	output_compare_update(C0A);
}

ISR(TIMER0_COMPB_vect) {
	output_compare_update(C0B);
}

void init_usart(void)
{
	/* set baud rate to 115200 */
	UBRR0H = 0;
	UBRR0L = 16;
	/* set comm rate to doubling */
	set(UCSR0A,U2X0);
	/* Enable receiver and transmitter */
	set(UCSR0B,RXEN0,TXEN0);
	/* Set frame format: 8data, 1stop bit */
	set(UCSR0C,UCSZ01,UCSZ00);
}

void init_dac(void) {
	// set CLK, DIN, ~CS to output
	set(DDRB,DDB5,DDB4,DDB3);
	// disable chip select
	set(PORTB,CS);
	// initialize clk low
	unset(PORTB,CLK);
}

void write_dac(uint16_t output) {
	// start data transfer
	unset(PORTB,CS);
	for (int i = 0; i < 16; i++) {
		if (get_bit(output,16-1-i)) {
			set(PORTB,DIN);
		}
		else {
			unset(PORTB,DIN);
		}
		set(PORTB,CLK);
		unset(PORTB,CLK);
	}
	set(PORTB,CS);
	dac = output;
}

// initialize trigger for opto-interrupter
void init_input_capture(void) {
	// enable pullup resistor on input capture port
	PORTB |= (1<<PORTB0);
	// trigger input capture on falling edge, enable noise filtering
	TCCR1B |= (0<<ICNC1)|(1<<ICES1);
	// register input capture interrupt;
	TIMSK1 |= 1 << ICIE1;
}

// serial communication functions
unsigned char data_available(void) {
	return get_bit(UCSR0A,RXC0);
}

unsigned char _read(unsigned char* data) {
	unsigned char status = UCSR0A;
	*data = UDR0;
	return status;
}

unsigned char read(unsigned char* data) {
	while (!data_available());
	return _read(data);
}

unsigned char read_bytes(uint8_t nbytes,uint8_t* bytes) {
	uint8_t status = 0, data;
	for (int i = 0; i < nbytes; i++) {
		status = read(&data);
		bytes[i] = data;
	}
	return status;
}

unsigned char output_ready(void) {
	return get_bit(UCSR0A,UDRE0);
}

void _write(unsigned char data) {
	UDR0 = data;
}

void write(unsigned char data) {
	while (!output_ready());
	_write(data);
}

void write_bytes(uint8_t nbytes, uint8_t bytes[]) {
	for (int i = 0; i < nbytes; i++) {
		write(bytes[i]);
	}
}

// compute delay between opto-interrupter trigger and next output compare
uint16_t get_delay(void) {
	Counter* counter = counters + C1A;
	uint16_t delay = get_oc(counter) - ICR1;
	return delay < counter->remainder ? delay : ~delay + 1;
}

// servo variables
volatile uint16_t delay;
volatile uint16_t previous;
volatile bool triggered = false;
volatile bool locking = false;
uint16_t setpoint; 

// on opto-interrupter trigger
ISR(TIMER1_CAPT_vect) {
	previous = delay;
	delay = get_delay();
	if (locking) {
		triggered = true;
	}
}

// in case we want digital line (for e.g. debugging)
void init_io(void) {
	set(DDRC,DDC0);
}

// initialize servo
void init_feedback(void) {
	setpoint = counters[C1A].remainder / 2;
	delay = counters[C1A].remainder;
	previous = delay;
}

// setpoint toggling (for testing) variables
bool stepping = false;
bool step_toggle = false;
uint16_t step_period = 1000;
uint16_t step_counter = 0;

// PI feedback algorithm variables
uint8_t c_phase = 120, c_freq = 125;
int32_t sign = -1;
int main(void)
{
	init_dac();
	init_io();
	init_usart();
	write_dac(DAC0);
	init_timers();
	init_feedback();
	init_input_capture();
	sei();
	uint16_t period = counters[C1A].remainder;
	uint8_t status, data;
	int32_t dac_p, delayo, previouso, setpointo;
	bool positive;
	while (1) {
		// if we are in locking mode, have new trigger, and have a previous trigger
		if (locking && triggered && previous < period) {
			triggered = false;
			// disable interrupts when accessing multi-byte registers
			cli();
			delayo = delay;
			previouso = previous;
			sei();
			// NOTE: the code computing the servo update to the dac is *NOT* optimized
			// 32 bit computations perhaps unnecessary
			setpointo = setpoint;
			dac_p = dac;
			// add contribution acting to stabilize phase ("integral" term)
			dac_p += sign * 20 * c_freq * (delayo - previouso);
			// add contribution acting to stabilize frequency ("proportional" term)
			dac_p += sign * c_phase * (delayo - setpoint) / 3;
			if (dac_p < DACMIN) {
				dac_p = DACMIN;
			}
			else if (dac_p > DACMAX) {
				dac_p = DACMAX;
			}
			write_dac(dac_p);
			if (stepping) {
				step_counter++;
				if (step_counter == step_period) {
					step_counter = 0;
					step_toggle = !step_toggle;
					setpoint = (step_toggle ? 3 : 2) * (period / 4);
				}
			}
			set(PINC,PINC0);
			continue;
		}
		if (!data_available()) {
			continue;
		}
		status = read(&data);
		// read dac value to set
		if (data == 'd') {
			uint16_t dac_value;
			// user must send immediately (e.g. at same time as 'd') or code will hang
			read_bytes(2,&dac_value);
			write_dac(dac_value);
		}
		// send current delay in counter units between opto-interrupter and next output compare
		else if (data == 'D') {
			cli();
			delayo = delay;
			sei();
			write_bytes(2,&delayo);
		}
		// send period of half cycle in counter units
		else if (data == 'p') {
			write_bytes(2,&period);
		}
		// send servo loop setpoint delay in counter units
		else if (data == 's') {
			write_bytes(2,&setpoint);
		}
		// turn on locking
		else if (data == 'l') {
			locking = true;
		}
		// turn off locking
		else if (data == 'u') {
			triggered = false;
			locking = false;
			step_toggle = false;
			setpoint = period / 2;
		}
		// send current dac value
		else if (data == 'r') {
			write_bytes(2,&dac);
		}
		// toggle setpoint stepping mode
		else if (data == 't') {
			stepping = !stepping;
		}
		// send feedback gain for integral term
		else if (data == 'Z') {
			write_bytes(1,&c_phase);
		}
		// read from stream and set feedback gain for integral term
		else if (data == 'z') {
			// send at same time as 'z' to avoid blocking program execution
			read_bytes(1,&c_phase);
		}
		// send feedback gain for proportional term
		else if (data == 'F') {
			write_bytes(1,&c_freq);
		}
		// read from stream and set feedback gain for proportional term
		else if (data == 'f') {
			// send at same time as 'z' to avoid blocking program execution
			read_bytes(1,&c_freq);
		}
		// request phase shift of C1 with respect to C0A and C0B (shift amount in counter units hardcoded in step_value variable)
		// 'h': increase phase, 'H': decrease phase
		else if (data == 'h' || data == 'H') {
			if (shift_signal == SHIFT_IDLE) {
				shift_sign = data == 'h' ? +1 : -1;
				shift_signal = SHIFT_REQUESTED;
				// request successful
				write(0x01);	
			}
			else {
				// phase shift already in progress
				write(0x00);
			}
		}
		else if (data == 'L') {
			write_bytes(1,&locking);
		}
	}
}
