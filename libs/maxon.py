import ctypes as c
from ctypes import wintypes as w
import os
import beckutil

dllname = 'EposCmd64.dll'
dll = beckutil.load_dll(dllname)

HOMING = 6
VELOCITY = -2
RPM = 0xa4
VN_STD = 0x00

bufsize = 1024
err = w.DWORD()

dname = b'EPOS2'
pname = b'MAXON SERIAL V2'
iname = b'USB'
portname = b'USB0'
nodeid = 1

def get_error_info(errorcode):
    errinfo = c.create_string_buffer(bufsize)
    dll.VCS_GetErrorInfo(
        errorcode,
        errinfo,
        bufsize
    )
    return errinfo.value

class MaxonError(Exception):
    def __init__(self,code,msg):
        self.code = code
        self.msg = msg
        super().__init__()

    def __str__(self):
        return '{}:\t{}'.format(hex(self.code),self.msg)

    def __repr__(self):
        return str(self)

def maxon(f,args):
    err = w.DWORD()
    success = f(*args,c.byref(err))
    if not success:
        raise MaxonError(
            err.value,
            get_error_info(err.value)
        )
    return success

def open_motor():
    return maxon(
        dll.VCS_OpenDevice,
        (
            dname,
            pname,
            iname,
            portname
        )
    )

def close_motor(handle):
    return maxon(
        dll.VCS_CloseDevice,
        (
            handle,
        )
    )

M_HOMING = 6
M_VELOCITY = -2
M_POSITION = -1
M_PROFILE_VELOCITY = 3
def get_operation_mode(handle):
    mode = c.c_char()
    maxon(
        dll.VCS_GetOperationMode,
        (
            handle,
            nodeid,
            c.byref(mode)
        )       
    )
    return mode.value

def set_operation_mode(handle,mode):
    return maxon(
        dll.VCS_SetOperationMode,
        (
            handle,
            nodeid,
            mode
        )
    )

V_ZERO = 0
V_DECI = -1
V_CENTI = -2
V_MILLI = -3
def set_velocity_units(handle,units):
    return maxon(
        dll.VCS_SetVelocityUnits,
        (
            handle,
            nodeid,
            RPM,
            units
        )
    )

def get_velocity_units(handle):
    vdim = w.BYTE()
    vnot = c.c_int8()
    maxon(
        dll.VCS_GetVelocityUnits,
        (
            handle,
            nodeid,
            c.byref(vdim),
            c.byref(vnot)
        )
    )
    return vnot.value

units_d = {
    V_ZERO:0,
    V_DECI:-1,
    V_CENTI:-2,
    V_MILLI:-3
}

def load_velocity(vel,units):
    return vel * 10**units_d[units]

lv = load_velocity

def dump_velocity(vel,units):
    return int(vel / 10**units_d[units])

dv = dump_velocity

def get_velocity_set(handle,units):
    velset = c.c_long()
    maxon(        
        dll.VCS_GetVelocityMust,
        (
            handle,
            nodeid,
            c.byref(velset)
        )
    )
    return lv(velset.value,units)

def get_velocity_act(handle,units):
    velact = c.c_long()
    maxon(
        dll.VCS_GetVelocityIs,
        (
            handle,
            nodeid,
            c.byref(velact)
        )
    )
    return lv(velact.value,units)

def get_velocity_act_avg(handle,units):
    vavg = c.c_long()
    maxon(
        dll.VCS_GetVelocityIsAveraged,
        (
            handle,
            nodeid,
            c.byref(vavg)
        )
    )
    return lv(vavg.value,units)

def set_velocity(handle,vel,units):
    return maxon(
        dll.VCS_SetVelocityMust,
        (
            handle,
            nodeid,
            dv(vel,units)
        )        
    )

def get_position_act(handle):
    pos = c.c_long()
    maxon(
        dll.VCS_GetPositionIs,
        (
            handle,
            nodeid,
            c.byref(pos)
        )
    )
    return pos.value

def get_position_set(handle):
    pos = c.c_long()
    maxon(
        dll.VCS_GetPositionMust,
        (
            handle,
            nodeid,
            c.byref(pos)
        )
    )
    return pos.value

def set_position(handle,pos):
    return maxon(
        dll.VCS_SetPositionMust,
        (
            handle,
            nodeid,
            pos
        )
    )

H_INDEX_POS_SPEED = 34
def find_home(handle):
    return maxon(
        dll.VCS_FindHome,
        (
            handle,
            nodeid,
            H_INDEX_POS_SPEED
        )
    )

def stop_homing(handle):
    return maxon(
        dll.VCS_StopHoming,
        (
            handle,
            nodeid
        )
    )

def get_homing_state(handle):
    homing_attained = w.BOOL()
    homing_error = w.BOOL()
    maxon(
        dll.VCS_GetHomingState,
        (
            handle,
            nodeid,
            c.byref(homing_attained),
            c.byref(homing_error)
        )
    )
    return homing_attained.value, homing_error.value

# dt in milliseconds (integer)
def set_velocity_window(handle,dvel,units,dt):
    return maxon(
        dll.VCS_EnableVelocityWindow,
        (
            handle,
            nodeid,
            dv(dvel,units),
            dt
        )
    )
        
def disable_velocity_window(handle):
    return maxon(
        dll.VCS_DisableVelocityWindow,
        (
            handle,
            nodeid
        )
    )

def move_with_velocity(handle,vel,units):
    return maxon(
        dll.VCS_MoveWithVelocity,
        (
            handle,
            nodeid,
            dv(vel,units)
        )
    )

def halt_velocity_movement(handle):
    return maxon(
        dll.VCS_HaltVelocityMovement,
        (
            handle,
            nodeid
        )
    )

def get_enabled_state(handle):
    enabled = w.BOOL()
    maxon(
        dll.VCS_GetEnableState,
        (
            handle,
            nodeid,
            c.byref(enabled)
        )
    )
    return enabled.value

def set_enabled_state(handle,enable):
    return maxon(
        (
            dll.VCS_SetEnableState
            if enable else
            dll.VCS_SetDisableState
        ),
        (
            handle,
            nodeid
        )
    )

# does not work for M_POSITION or
# M_VELOCITY modes
def get_movement_state(handle):
    target_reached = w.BOOL()
    maxon(
        dll.VCS_GetMovementState,
        (
            handle,
            nodeid,
            c.byref(target_reached)
        )
    )
    return target_reached.value

# does not work for M_POSITION or
# M_VELOCITY modes
# timeout in milliseconds
def wait_for_target_reached(handle,timeout):
    return maxon(
        dll.VCS_WaitForTargetReached,
        (
            handle,
            nodeid,
            timeout
        )
    )

if __name__ == '__main__':
    cont = input('continue to velocity + homing test? (y/(n)): ')
    if not cont or cont[0].lower() != 'y':
        exit()
    from time import sleep
    # get handle to motor
    h = open_motor()
    v1 = 50
    v2 = 0
    vsets = (v1,v2)
    try:
        # motor must be disbled before configuration
        set_enabled_state(h,False)
        # motor measures and sets speed accurate to milli-rpm
        set_velocity_units(h,V_MILLI)
        # query velocity units (should return V_MILLI)
        units = get_velocity_units(h)
        # set window to define when target velocity reached
        set_velocity_window(h,2.0,units,100)
        # put motor into velocity profile mode
        set_operation_mode(h,M_PROFILE_VELOCITY)
        # enable motor
        set_enabled_state(h,True)
        for vset in vsets:
            # set velocity
            move_with_velocity(h,vset,units)
            print('starting change to velocity {:.3f} rpm'.format(vset))
            # query motor to see if target velocity reached
            while not get_movement_state(h):
                # read current averaged velocity
                vact = get_velocity_act_avg(h,units)
                print(
                    ',\t'.join(
                        '{}: {:.3f} rpm'.format(label,vel)
                        for label, vel in (
                                ('vset',vset),
                                ('vact',vact),
                        )
                    )
                )
                sleep(.100)
            print('velocity of {:.3f} rpm reached.'.format(vset))
        # disable motor to configure
        set_enabled_state(h,False)
        # set to homing mode
        set_operation_mode(h,M_HOMING)
        # enable motor
        set_enabled_state(h,True)
        # start homing
        find_home(h)
        print('starting homing')
        while True:
            # get status of homing procedure
            homing_attained, homing_error = get_homing_state(h)
            if homing_error:
                raise Exception('homing error')
            if homing_attained:
                break
            # read current position
            pos = get_position_act(h)
            print('position: {:d} steps'.format(pos))
            sleep(.200)
        print('homing successful. press enter to quit')
        input()
        pos = get_position_act(h)
        print('final position: {:d} steps'.format(pos))
    finally:
        # make sure we turn off motor
        set_enabled_state(h,False)
        print('motor disabled')
        # make sure we disconnect from motor
        close_motor(h)
        print('motor disconnected')
    
