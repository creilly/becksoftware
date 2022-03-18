import pyvisa
from time import sleep

FLAGNAME = 'flag'

PARAM_S = 100
PARAM_T = 101
PARAM_R = 1

TERM_CHAR = '\r'

class FlagHandler:
    def __init__(self,flagname=FLAGNAME):
        self.flag = flag = pyvisa.ResourceManager().open_resource(flagname)
        flag.stop_bits = pyvisa.constants.StopBits.two        
        flag.data_bits = 7
        flag.parity = pyvisa.constants.Parity.odd
        flag.read_termination = TERM_CHAR
        flag.write_termination = TERM_CHAR    

    def __enter__(self):
        return self.flag

    def __exit__(self,*args):
        self.flag.close()

def get_version(flag):
    return flag.query('V4')

def get_position(flag):
    return int(flag.query('V1')[1:].strip())

def get_temperature_status(flag):
    return flag.query('V3')

def get_dynamic_parameters(flag):
    flag.write('V5')
    lines = 4
    line = 0
    resp = []
    while line < lines:
        resp.append(flag.read())
        line += 1
    return resp

def set_dynamic_parameters(flag,s,t,r):
    command = 'X{}'.format(
        ','.join(
            map(
                '{:d}'.format,
                (s,t,r)
            )
        )
    )
    oldtimeout = flag.timeout
    flag.timeout = 2e3    
    resp = flag.query(command)
    flag.timeout = oldtimeout
    return(resp)

def set_holding_torque(flag,torque):
    return flag.query('h10,{:d}'.format(torque))

def initialize(flag):
    return set_dynamic_parameters(flag,PARAM_S,PARAM_T,PARAM_R)

def intialize_counters(flag):
    return flag.query('I1')

BLOCKED = 0
UNBLOCKED = +3
def set_position(flag,position):
    return flag.query('G{:+d}'.format(position))

if __name__ == '__main__':
    with FlagHandler() as flag:
        print(get_position(flag))
    
    
