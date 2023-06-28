import pyvisa as visa
from time import sleep

TERM_CHAR = '\n'
DEVNAME = 'pi'

X, Y = 1, 2

def open_pi():
    dev = visa.ResourceManager().open_resource(DEVNAME)
    dev.baud_rate = 115200
    dev.read_termination = dev.write_termination = TERM_CHAR    
    return dev

def close_pi(dev):
    dev.close()

# def idn(dev,add):
#     return get_parameter(dev,add,'*idn')

def get_motor_state(dev,add):
    return bool(int(get_parameter(dev,add,'svo')))

def set_motor_state(dev,add,state):
    return set_parameter(dev,add,'svo',str(int(state)))

def get_parameter(dev,add,param):
    return dev.query(
        '{:d} {}?'.format(add,param)
    ).strip().split('=')[1]

def send_command(dev,add,cmd):
    return dev.write(
        '{:d} {}'.format(add,cmd)
    )

def set_parameter(dev,add,param,value):
    return send_command(
        dev,add,'{} 1 {}'.format(param,value)
    )

def get_position(dev,add):
    return float(get_parameter(dev,add,'pos'))

def set_ref_position(dev,add,position):
    set_ref_mode(dev,add,0)
    return set_parameter(dev,add,'pos',str(position))

def get_ref_mode(dev,add):
    return int(get_parameter(dev,add,'ron'))

def set_ref_mode(dev,add,mode):
    return set_parameter(dev,add,'ron',str(mode))

def set_position(dev,add,position):
    return set_parameter(dev,add,'mov',str(position))

def get_on_target_state(dev,add):
    return bool(int(get_parameter(dev,add,'ont')))

def home_motor(dev,add):
    set_ref_mode(dev,add,1)
    send_command(dev,add,'fnl')

def wait_motor(dev,add,sleep_time=None,cb=None):
    while not get_on_target_state(dev,add):
        if cb is not None:
            cb()
        if sleep_time is not None:
            sleep(sleep_time)

def get_velocity(dev,add):
    return float(get_parameter(dev,add,'vel'))

def set_velocity(dev,add,vel):
    return set_parameter(dev,add,'vel',str(vel))

class PIHandler:
    def __enter__(self):
        self.dev = open_pi()
        return self.dev

    def __exit__(self,*args):
        close_pi(self.dev)

if __name__ == '__main__':
    with PIHandler() as dev:
        for add in (1,2):
            print('position {:d}:'.format(add),get_position(dev,add))
        # for add in (1,2):
        #     set_motor_state(dev,add,True)
        #     home_motor(dev,add)
        # for add in (1,2):
        #     wait_motor(dev,add)
        #     set_position(dev,add,25.0)
        # for add in (1,2):
        #     wait_motor(dev,add)
        #     set_motor_state(dev,add,False)
