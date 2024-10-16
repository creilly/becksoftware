import serial, time, struct, msvcrt, numpy as np

msport = 'COM7'

vref = 2.048 # volts

class MotorSyncHandler:
    def __init__(self):
        self.ms = open_ms()

    def __enter__(self):
        return self.ms

    def __exit__(self,*args):
        close_ms(self.ms)

def open_ms():   
    ms = serial.Serial(msport,115200,dsrdtr=None,timeout=1)
    return ms

def close_ms(ms):
    ms.close()

coeffd = {'z':'phase','f':'freq'}

def read(ms,bytes):
    return ms.read(bytes)

def write(ms,msg):
    ms.write(msg)

def parse_uint(rawbytes):
    return int.from_bytes(rawbytes,byteorder='little')

def format_uint(uint,bytes):
    return struct.pack({1:'B',2:'H'}[bytes],uint)

def read_uint(ms,bytes):
    return parse_uint(read(ms,bytes))

def send_command(ms,c,data=b''):
    write(ms,c+data)

def query(ms,c,bytes):
    send_command(ms,c)
    return read_uint(ms,bytes)

def get_period(ms):
    return query(ms,b'p',2)

def get_delay(ms):
    return query(ms,b'D',2)

def get_dac(ms):
    return query(ms,b'r',2)

def get_dac_voltage(ms):
    return get_dac(ms) / 2**16 * 2 * vref
    
def set_dac(ms,dac):
    send_command(ms,b'd',format_uint(dac,2))

def set_dac_voltage(ms,dacv):
    set_dac(ms,int(round(dacv/(2*vref)*2**16)))

def get_setpoint(ms):
    return query(ms,b's',2)

def set_locking(ms):
    send_command(ms,b'l')

def set_unlocking(ms):
    send_command(ms,b'u')

def get_locking(ms):
    return bool(query(ms,b'L',1))

def toggle_setpoint_toggling(ms):
    send_command(ms,b't')

FORWARDS, BACKWARDS = 0, 1
def shift_phase(ms,direction):
    send_command(ms,{FORWARDS:b'h',BACKWARDS:b'H'}[direction])

def set_phase_gain(ms,gain):
    send_command(ms,b'z',format_uint(gain,1))

def set_freq_gain(ms,gain):
    send_command(ms,b'f',format_uint(gain,1))

def get_phase_gain(ms):
    return query(ms,b'Z',1)

def get_freq_gain(ms):
    return query(ms,b'F',1)