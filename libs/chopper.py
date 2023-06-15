import maxon
import time

maxon_open = 0
maxon_closed = 20

def start_halt(mh):
    maxon.set_halting(mh,True)

def wait_state(mh,state_function,sleep_time,callback=None):
    while not state_function(mh):
        if callback is not None:
            callback(mh)
        time.sleep(sleep_time)

def wait_movement(mh,sleep_time=0.0,callback=None):
    wait_state(mh,maxon.get_movement_state,sleep_time,callback)

def is_homed(mh):
    homing_attained, homing_error = maxon.get_homing_state(mh)
    if homing_error:
        raise Exception('error during homing')
    return homing_attained

def start_home(mh):
    maxon.set_operation_mode(mh,maxon.M_HOMING)
    maxon.find_home(mh)

# user callback received motor handle
def wait_home(mh,sleep_time=0.0,callback=None):
    wait_state(mh,is_homed,sleep_time,callback)

def set_blocking(mh,blocking):
    maxon.set_operation_mode(mh,maxon.M_PROFILE_POSITION)
    maxon.move_to_position(mh,{True:maxon_closed,False:maxon_open}[blocking])

def start_spin(mh,v_chop):
    units = maxon.get_velocity_units(mh)
    maxon.set_operation_mode(mh,maxon.M_PROFILE_VELOCITY)
    maxon.set_enabled_state(mh,True)    
    maxon.move_with_velocity(mh,v_chop,units)  

def freq_to_vel(freq):
    return freq * 60 / 2

def _velcb(veltar,units):    
    def __velcb(mh):
        print(
            ', '.join(
                [
                    '{}: {:.1f} rpm'.format(
                        label,vel
                    ) for label, vel in (
                        ('target velocity', veltar),
                        ('actual velocity', maxon.get_velocity_act(mh,units))
                    )
                ]
            )
        )
    return __velcb

def wait_spin(mh,sleep_time=0.0):    
    units = maxon.get_velocity_units(mh)    
    veltar = maxon.get_target_velocity(mh,units)
    wait_movement(mh,sleep_time,_velcb(veltar,units))

def wait_halt(mh,sleep_time=0.0):
    units = maxon.get_velocity_units(mh)
    wait_movement(mh,sleep_time,_velcb(0.0,units))

if __name__ == '__main__':
    with maxon.MaxonHandler() as mh:
        print('halting.')
        start_halt(mh)
        wait_halt(mh)
        print('halted.')