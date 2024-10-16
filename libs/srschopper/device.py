import serial, struct

comport = 17
baudrate = 115200
stopbits = 1

greeting = 'jello, gurl!'

fclk = 16e6 # Hz
prescalar = 8
nbytes_delay = 2

vmax = 5.0 # volts
nbytes_control = 2

DELAY = 'y'
CONTROL = 'c'
FCOEFF = 'f'
DCOEFF = 'd'
LOCKING = 'l'
SETPOINT = 's'
OPTO = 'o'
REF = 'r'

# in seconds
def format_delay(delay_seconds):
    return int(round(delay_seconds * fclk / prescalar)) # clock cycles

# in clock cycles
def parse_delay(delay_cycles):
    return delay_cycles / fclk * prescalar # seconds

class SRSChopperHandler():
    def __enter__(self):
        self.ser = open()
        return self.ser
    def __exit__(self,*args,**kwargs):
        close(self.ser)

def open():
    ser = serial.Serial('COM{:d}'.format(comport),baudrate=baudrate,stopbits=stopbits)    
    ser.timeout = 0.25
    while True:
        greetingp = get_greeting(ser)            
        if greetingp == greeting:            
            break
    while ser.read(): continue
    return ser
        
def close(s):
    s.close()

def write(s,msg):
    s.write(msg)

def read_bytes(s,nbytes):
    return parse_bytes(s.read(nbytes))

def parse_bytes(bytes):
    parsed_bytes = int.from_bytes(bytes,'little')    
    return parsed_bytes

def query_value(s,command_char,nbytes):
    write(s,command_char.upper().encode())
    return read_bytes(s,nbytes)

def set_value(s,command_char,nbytes,value):    
    header = command_char.lower().encode()
    fmtstr = '<' + 'B'*nbytes
    intarr = [
        (value >> 8 * nbyte)%(1 << 8) 
        for nbyte in range(nbytes)
    ]    
    packed = struct.pack(fmtstr,*intarr)    
    command = header + packed    
    write(s,command)

def get_greeting(s):
    write(s,b'G')
    greeting = b''
    while True:
        b = s.read()        
        if not b:
            return None
        if b == b'\0':
            return greeting.decode()
        greeting += b

# seconds
def get_delay(s):
    return parse_delay(
        query_value(
            s,DELAY,2
        )
    )

# volts
def get_control(s):
    return query_value(
        s,CONTROL,2
    ) * vmax / (1 << (8 * 2))

def set_control(s,control):
    return set_value(
        s,CONTROL,2,int(
            round(
                control / vmax * (1 << (2*8))
            )
        )
    )

# in volts
def get_locking(s):
    return bool(query_value(s,LOCKING,1))

def set_locking(s,locking):
    set_value(s,LOCKING,1,int(locking))

# in seconds
def get_setpoint(s):
    return parse_delay(
        query_value(
            s,SETPOINT,2
        )
    )

def set_setpoint(s,setpoint):
    set_value(
        s,SETPOINT,2,format_delay(setpoint)
    )

# 0-255
def get_f_coeff(s):
    return query_value(s,FCOEFF,1)
def set_f_coeff(s,f_coeff):
    set_value(s,FCOEFF,1,f_coeff)

# 0-255
def get_d_coeff(s):
    return query_value(s,DCOEFF,1)
def set_f_coeff(s,d_coeff):
    set_value(s,FCOEFF,1,d_coeff)

# 0-255
def get_ref_count(s):
    return query_value(s,REF,1)

# 0-255
def get_opto_count(s):
    return query_value(s,OPTO,1)

if __name__ == '__main__':    
    import time
    with SRSChopperHandler() as s:        
        set_control(s,2.3)        
        while True:
            print(get_control(s),get_delay(s))
