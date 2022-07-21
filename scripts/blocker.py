from maxon import M_PROFILE_POSITION
import maxon

class Blocker:
    def __init__(self,maxon_handle,blocking):
        self.maxon_handle = maxon_handle
        self.blocking = blocking

    def set_mode(self,requested_mode):
        current_mode = maxon.get_operation_mode(self.maxon_handle)
        if current_mode == requested_mode:
            return
        self.quick_stop()
        maxon.set_operation_mode(self.maxon_handle,requested_mode)

    def wait_target(self):
        while not maxon.get_movement_state(self.maxon_handle):
            continue        

    def quick_stop(self):
        maxon.set_quick_stop_state(self.maxon_handle)
        self.wait_target()

    def __enter__(self):
        self.set_mode(maxon.M_HOMING)
        homing_attained, homing_error = maxon.get_homing_state(self.maxon_handle)
        if homing_error:
            raise Exception('homing error: {:d}'.format(homing_error))
        if not homing_attained:
            print('homing not attained')
            self.set_mode(maxon.M_HOMING)
            maxon.set_enabled_state(self.maxon_handle,True)
            maxon.find_home(self.maxon_handle)
            self.wait_target()
        self.set_mode(M_PROFILE_POSITION)        

    def __exit__(self,*args):
        print('exiting')

if __name__ == '__main__':
    with maxon.MaxonHandler() as mh:
        with Blocker(mh,True) as blocker:
            print('blocker',blocker)