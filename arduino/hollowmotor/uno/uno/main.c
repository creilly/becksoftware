/*
 * uno.c
 *
 * Created: 1/3/2023 11:27:39 AM
 * Author : reilly
 */ 

#define F_CPU 16000000UL // clock speed
#define F_FUND 2370.0 // HERTZ
#define PRESCALAR1 8
#define PRESCALAR0 8
#define SUB0A 6
#define SUB0B 10
#define SUB1 40
#define C1 0
#define C0A 1
#define C0B 2

#define DBDF_DAC 32768 // bits per hertz
#define DBDF_TIM
#define DAMPING 3 // feedback reduction
#define DAC0 (1L << 15) // initial dac value

#define CLK PORTB5
#define DIN PORTB4
#define CS PORTB3

#define bor(x, ...) _bor(x, __VA_ARGS__)
#define set(p, ...) p |= bor(__VA_ARGS__, -1)
#define unset(p, ...) p &= ~(bor(__VA_ARGS__, -1))
#define get_bit(B,b) (((B) >> (b)) & 1)
#define round(x,y) (y)((x) + 0.5)

#include <avr/io.h>
#include <avr/interrupt.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdbool.h>

typedef struct Counters {
	uint16_t cycles, remainder, period;
	volatile uint16_t cycle;
	volatile bool state;
	uint8_t oc_reg, state_bit, tc_reg, bytes;
} Counter;

uint16_t dac;

Counter counters[3];

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

volatile uint16_t get_reg(uint8_t add, uint8_t bytes) {
	uint16_t result = 0;
	volatile uint8_t* subadd = add;
	for (int i = 0; i < bytes; i++) {
		result |= (uint16_t)(*subadd) << (i * 8);
		subadd += 1;
	}
	return result;
}

void set_oc(Counter* counter, volatile uint16_t state) {
	set_reg(counter->oc_reg,state,counter->bytes);
}

volatile uint16_t get_oc(Counter* counter) {
	return get_reg(counter->oc_reg, counter->bytes);
}

void toggle_bit(uint8_t add, uint8_t bit, uint8_t state) {
	volatile uint8_t* reg = add;
	if (state) {
		*reg |= 1 << bit;
	}
	else {
		*reg &= ~(1 << bit);
	}
}

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

void init_timers(void) {
	// disable prescalar
	set(GTCCR,TSM);
		
	// reset prescalar
	set(GTCCR,PSRSYNC);
	
	uint8_t prescalaro = PRESCALAR0 > PRESCALAR1 ? PRESCALAR0 : PRESCALAR1;
	uint32_t periodo = round(F_CPU/F_FUND/2/prescalaro,uint32_t);
	uint32_t period;
	uint32_t divisor;
	uint8_t subharmonic, tc_bit;
	for (int i = 0; i < 3; i++) {
		uint16_t prescalar = i == C1 ? PRESCALAR1 : PRESCALAR0;
		Counter* counter = counters + i;
		counter->bytes = i == C1 ? 2 : 1;
		divisor = 1L << (8 * counter->bytes);
		counter->state = false;
		counter->tc_reg = i == C1 ? &TCCR1A : &TCCR0A;
		set_ps(i == C1 ? &TCCR1B : &TCCR0B, prescalar, i == C1 ? CS10 : CS00);
		switch (i) {
			case C1:
				subharmonic = SUB1;
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
		toggle_bit(counter->tc_reg,tc_bit,true);
		period = periodo * prescalaro / prescalar * subharmonic;
		get_largest_remainder(period,1L << (counter->bytes * 8),&counter->period,&counter->remainder,&counter->cycles);
		counter->cycle = counter->cycles;
		set_oc(counter,counter->remainder);
	}
	
	// set counter0 output compare pins to output
	set(DDRD,DDD6,DDD5);
	
	// set counter1 output compare pins to output
	set(DDRB,DDB2);
	
	// enable interrupt for counter0 comp matches
	set(TIMSK0,OCIE0A,OCIE0B);
	
	// enable interrupt for counter1 comp match
	set(TIMSK1,OCIE1B);
	
	// enable counters
	unset(GTCCR,TSM);
}

void toggle_counter(Counter* counter) {
	toggle_bit(counter->tc_reg,counter->state_bit,counter->state);
	counter->state = !counter->state;
}

void increment_oc(Counter* counter, uint16_t delta) {
	set_oc(counter,get_oc(counter) + delta);
}

void output_compare_update(uint8_t counter_index) {
	Counter* counter = counters + counter_index;
	uint16_t cycle = counter->cycle--;
	if (cycle == 0) {
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

ISR(TIMER1_COMPB_vect) {
	output_compare_update(C1);
}

ISR(TIMER0_COMPA_vect) {
	output_compare_update(C0A);
}

ISR(TIMER0_COMPB_vect) {
	output_compare_update(C0B);
}

void init_usart(void)
{
	/*Set baud rate */
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

void init_input_capture(void) {
	// enable pullup resistor on input capture port
	PORTB |= (1<<PORTB0);
	// trigger input capture on falling edge, enable noise filtering
	TCCR1B |= (0<<ICNC1)|(1<<ICES1);
	// register input capture interrupt;
	TIMSK1 |= 1 << ICIE1;
}

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

uint16_t get_delay(void) {
	Counter* counter = counters + C1;
	uint16_t delay = get_oc(counter) - ICR1;
	return delay < counter->remainder ? delay : ~delay + 1;
}

volatile uint16_t delay;
volatile uint16_t previous;
volatile bool triggered = false;
volatile bool locking = false;
uint16_t setpoint; 
ISR(TIMER1_CAPT_vect) {
	previous = delay;
	delay = get_delay();
	if (locking) {
		triggered = true;
	}
}

void init_io(void) {
	set(DDRC,DDC0);
}

void init_feedback(void) {
	setpoint = counters[C1].remainder / 2;
	delay = counters[C1].remainder;
	previous = delay;
}
bool stepping = false;
bool step_toggle = false;
uint16_t step_period = 300;
uint16_t step_counter = 0;
uint16_t max_correction = 1L << 13;
uint8_t c_phase = 100, c_freq = 0;
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
	uint16_t period = counters[C1].remainder;
	uint8_t status, data;
	while (1) {
		if (locking && triggered && previous < period) {
			triggered = false;
			cli();
			uint16_t delayo = delay;
			uint16_t previouso = previous;
			bool positive = delay > setpoint;
			uint32_t correction = (positive ? delay - setpoint : setpoint - delay) / c_phase;
			if (correction > max_correction) {
				correction = max_correction;
			}
			sei();
			// damping factor 8 for freq control, 100 for phase control
			write_dac(
				dac - ( 
					c_freq * (delayo - previouso) + 
					(positive ? +1 : -1)*correction 
				)
			);
			if (stepping) {
				step_counter++;
				if (step_counter == step_period) {
					step_counter = 0;
					step_toggle = !step_toggle;
					setpoint = (step_toggle ? 3 : 2) * (period / 4);
				}
			}
			continue;
		}
		if (!data_available()) {
			continue;
		}
		status = read(&data);
		if (data == 'd') {
			uint16_t dac_value;
			// user must send immediately (e.g. with 'd')
			read_bytes(2,&dac_value);
			write_dac(dac_value);
		}
		else if (data == 'D') {
			cli();
			uint16_t delayo = delay;
			sei();
			write_bytes(2,&delayo);
		}
		else if (data == 'p') {
			write_bytes(2,&period);
		}
		else if (data == 's') {
			write_bytes(2,&setpoint);
		}
		else if (data == 'l') {
			locking = true;
		}
		else if (data == 'u') {
			triggered = false;
			locking = false;
			step_toggle = false;
			setpoint = period / 2;
		}
		else if (data == 'r') {
			write_bytes(2,&dac);
		}
		else if (data == 't') {
			stepping = !stepping;
		}
		else if (data == 'Z') {
			write_bytes(1,&c_phase);
		}
		else if (data == 'z') {
			read_bytes(1,&c_phase);
		}
		else if (data == 'F') {
			write_bytes(1,&c_freq);
		}
		else if (data == 'f') {
			read_bytes(1,&c_freq);
		}
	}
}
