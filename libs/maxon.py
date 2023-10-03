from asyncio import wait_for
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

class MaxonHandler:
    def __enter__(self):
        self.h = open_motor()        
        return self.h

    def __exit__(self,*args):
        close_motor(self.h)        

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

def get_fault(handle):
    faulting = w.BOOL()
    maxon(
        dll.VCS_GetFaultState, 
        (
            handle, 
            nodeid,
            c.byref(faulting)
        )
    )
    return bool(faulting.value)

def clear_fault(handle):
    return maxon(
        dll.VCS_ClearFault,
        (
            handle,
            nodeid             
        )
    )

M_HOMING = 6
M_VELOCITY = -2
M_POSITION = -1
M_PROFILE_VELOCITY = 3
M_PROFILE_POSITION = 1
M_CURRENT = -3
def get_operation_mode(handle):
    mode = c.c_int8()
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

def get_object_word(handle,object_index,object_subindex):
    data = w.WORD()
    nbytesread = w.DWORD()    
    maxon(
        dll.VCS_GetObject,
        (
            handle, 
            nodeid, 
            object_index, 
            object_subindex,            
            c.byref(data), 
            2,
            c.byref(nbytesread)
        )
    )
    if nbytesread.value != 2:
        raise Exception('error during maxon word read')
    return data.value

STATUSWORD_INDEX = 0x6041
STATUSWORD_SUBINDEX = 0x00
def get_status_word(handle):
    return get_object_word(handle,STATUSWORD_INDEX,STATUSWORD_SUBINDEX)

CONTROLWORD_INDEX = 0x6040
CONTROLWORD_SUBINDEX = 0x00
def get_control_word(handle):
    return get_object_word(handle,CONTROLWORD_INDEX,CONTROLWORD_SUBINDEX)

CW_HALT = 8
def get_halt_bit(handle):
    return get_word_bit(get_control_word(handle),CW_HALT)

def get_word_bit(word,bit):
    return (word // 2**bit) % 2

SW_RDY_SW_ON, SW_SW_ON, SW_OP_EN, \
    SW_FLT, SW_VLT_EN, SW_QS, SW_SW_ON_DS, SW_WRN, \
        SW_OFF_CR_MS, SW_REM, SW_10, SW_INT_LM_AC, \
            SW_12, SW_13, SW_RCPS, SW_REF_HM = \
                0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
def get_status_bit(handle,bit):
    return get_word_bit(get_status_word(handle),bit)    

def get_homed(handle):
    return get_status_bit(handle,SW_REF_HM)

# profile velocity mode

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

def get_target_velocity(handle,units):
    target_velocity = c.c_long()
    maxon(
        dll.VCS_GetTargetVelocity,
        (
            handle, nodeid, c.byref(target_velocity)
        )
    )    
    return lv(target_velocity.value,units)

def halt_velocity_movement(handle):
    return maxon(
        dll.VCS_HaltVelocityMovement,
        (
            handle,
            nodeid
        )
    )

def set_word_bit(handle,index,subindex,bit_add,bit_val):
    wordo = get_object_word(handle,index,subindex)
    wordp = wordo + 2 ** bit_add * ( bit_val - get_word_bit(wordo,bit_add) )
    set_word(handle,index,subindex,wordp)

def set_word(handle,index,subindex,word):
    nbyteswritten = w.DWORD()
    maxon(
        dll.VCS_SetObject,
        (
            handle, nodeid, 
            index, subindex, 
            c.byref(w.WORD(word)), 
            2, 
            c.byref(nbyteswritten)
        )
    )
    if nbyteswritten.value != 2:        
        raise Exception('error during maxon word read')

def set_halting(handle,halting):
    return set_word_bit(handle,CONTROLWORD_INDEX,CONTROLWORD_SUBINDEX,CW_HALT,{True:1,False:0}[halting])

# profile position mode

def set_position_window(handle,dpos,dt):
    return maxon(
        dll.VCS_EnablePositionWindow,
        (
            handle,
            nodeid,
            dpos,
            dt
        )
    )

def move_to_position(handle,position):
    return maxon(
        dll.VCS_MoveToPosition,
        (
            handle,
            nodeid,
            position,
            1, # absolute
            1 # immediately
        )
    )

def get_target_position(handle):
    tp = c.c_long()
    maxon(
        dll.VCS_GetTargetPosition,
        (
            handle,
            nodeid,
            c.byref(tp)
        )
    )
    return tp.value

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

def set_quick_stop_state(handle):
    return maxon(
        dll.VCS_SetQuickStopState,
        (
            handle, 
            nodeid
        )
    )

def get_quick_stop_state(handle):
    state = w.BOOL()
    maxon(
        dll.VCS_GetQuickStopState,
        (
            handle, 
            nodeid, 
            c.byref(state)
        )
    )
    return state.value

def get_current_setpoint(handle):
    current = w.SHORT()
    maxon(
        dll.VCS_GetCurrentMust,
        (
            handle,
            nodeid,
            c.byref(current)
        )
    )
    return current.value

CURRENT_DEMAND_WORD = 0x2031
CURRENT_DEMAND_SUBINDEX = 0x00
def get_current_demand(handle):
    return get_object_word(handle,CURRENT_DEMAND_WORD,CURRENT_DEMAND_SUBINDEX)

if __name__ == '__main__':    
    with MaxonHandler() as h:  
        print('v units',get_velocity_units(h))
        exit()
    from time import time
    # with MaxonHandler() as h:
    #     print('v units:',get_velocity_units(h))
    # exit()
    cont = input('continue to velocity + homing test? (y/(n)): ')
    if not cont or cont[0].lower() != 'y':
        exit()
    from time import sleep
    vset = 8000
    dt = 100
    epsilonv = 2.0    
    with MaxonHandler() as h:  
        # motor must be disbled before configuration
        set_enabled_state(h,False)
        # motor measures and sets speed accurate to milli-rpm
        set_velocity_units(h,V_MILLI)
        # query velocity units (should return V_MILLI)
        units = get_velocity_units(h)
        # set window to define when target velocity reached
        set_velocity_window(h,epsilonv,units,dt)
        # put motor into velocity profile mode
        set_operation_mode(h,M_PROFILE_VELOCITY)
        # enable motor
        set_enabled_state(h,True)        
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
        print('quick stop state:',get_quick_stop_state(h))        
        print('enabled state:',get_enabled_state(h))
        set_quick_stop_state(h)
        print('enabled state:',get_enabled_state(h))
        print('quick stop started')
        print('quick stop state:',get_quick_stop_state(h))
        print('enabled state:',get_enabled_state(h))
        while not get_movement_state(h):            
            # read current averaged velocity
            vact = get_velocity_act(h,units)
            print(
                ',\t'.join(
                    '{}: {:.3f} rpm'.format(label,vel)
                    for label, vel in (
                            ('vset',0.0),
                            ('vact',vact),
                    )
                )
            )
            sleep(.100)
        print('quick stop state:',get_quick_stop_state(h))
        print('enabled state:',get_enabled_state(h))
        print('disabling motor')
        # disable motor to configure
        set_enabled_state(h,False)
        print('enabled state:',get_enabled_state(h))
        print('quick stop state:',get_quick_stop_state(h))
        print('setting to homing mode')
        # set to homing mode
        set_operation_mode(h,M_HOMING)
        print('enabled state:',get_enabled_state(h))
        print('quick stop state:',get_quick_stop_state(h))
        # enable motor
        print('enabling motor')
        set_enabled_state(h,True)
        print('enabled state:',get_enabled_state(h))
        print('quick stop state:',get_quick_stop_state(h))
        # start homing
        find_home(h)
        print('starting homing')
        tmax = 1.000
        tstart = time()
        aborted = False
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
            if time() - tstart > tmax:
                aborted = True                
                print('quick stop state:',get_quick_stop_state(h))
                set_quick_stop_state(h)
                print('quick stop started')
                print('quick stop state:',get_quick_stop_state(h))
                while not get_movement_state(h):            
                    # read current averaged velocity
                    vact = get_velocity_act(h,units)
                    print(
                        ',\t'.join(
                            '{}: {:.3f} rpm'.format(label,vel)
                            for label, vel in (
                                    ('vset',0.0),
                                    ('vact',vact),
                            )
                        )
                    )
                break        
        print('homing terminated')
        print('homing status:',get_homing_state(h))
        if aborted:
            print('homing aborted')
        else:
            print('homing not aborted')
        print('homing successful. press enter to quit')
        input()
        pos = get_position_act(h)
        print('final position: {:d} steps'.format(pos))        