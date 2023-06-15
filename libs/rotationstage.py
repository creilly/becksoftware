import ctypes as c
import ctypes.wintypes as w
from beckutil import load_dll
from beckasync import get_blocking, sleep

TCUBE_DC_SERVO = 83
KCUBE_DC_SERVO = 27

class RotationStageHandler:
    def __init__(self,sn=None,typeid=KCUBE_DC_SERVO):
        self.sn = open_device(sn,typeid)

    def __enter__(self):
        return self.sn

    def __exit__(self,*args):
        close_device(self.sn)

devinfo_fields = (
    ('typeID',w.DWORD),
    ('description', c.c_char*65),
    ('serialNo',c.c_char*16),
    ('PID',w.DWORD),
    ('isKnownType',c.c_bool),
    ('motorType', c.c_uint),
    ('isPiezoDevice',c.c_bool),
    ('isLaser',c.c_bool),
    ('isCustomType',c.c_bool),
    ('isRack',c.c_bool),
    ('maxChannels', c.c_short)
)
class DeviceInfo(c.Structure):
    _fields_ = devinfo_fields

class KinesisError(Exception):
    def __init__(self,code):
        self.code = code

    def __str__(self):
        return 'error code {0:d} ({0:#04X})'.format(self.code)

def k(f,args,success = False):
    err = f(*args)
    if bool(err) is not success:
        raise KinesisError(err)

kdllname = r'Thorlabs.MotionControl.KCube.DCServo.dll'
tdllname = r'Thorlabs.MotionControl.TCube.DCServo.dll'

dlls = {
    model:load_dll(fname) for model, fname in (
        (KCUBE_DC_SERVO,kdllname),
        (TCUBE_DC_SERVO,tdllname),
    )
}

def list_devices(typeid = KCUBE_DC_SERVO):
    dll = dlls[typeid]
    k(
        dll.TLI_BuildDeviceList,
        ()
    )    

    bufsize = 256
    sns = c.create_string_buffer(bufsize)

    k(
        dll.TLI_GetDeviceListByTypeExt,
        (
            sns,
            bufsize,
            typeid
        )
    )

    return list(filter(bool,sns.value.split(b',')))
    
def get_dev_info(sn):
    sn, dll = sn
    devinfo = DeviceInfo()
    k(
        dll.TLI_GetDeviceInfo,
        (
            sn,
            c.byref(devinfo)
        ),
        success = True
    )
    return devinfo

def fmt_dev_info(devinfo):
    return '\n'.join(
        '{:<15}:{:>30}'.format(x,str(getattr(devinfo,x))) for x in list(zip(*devinfo_fields))[0]
    )

def open_device(sn = None,typeid = KCUBE_DC_SERVO):
    dll = dlls[typeid]
    if sn is None:
        sns = list_devices(typeid)        
        if not sns:
            raise Exception('no devices connected')
        sn = sns[0]
    k(
        dll.CC_Open,
        (sn,)
    )
    sn = sn, dll
    load_settings(sn)
    return sn

def close_device(sn):
    sn, dll = sn
    dll.CC_Close(sn)

def get_motor_params(sn):
    sn, dll = sn
    spr = c.c_double()
    gbr = c.c_double()
    pitch = c.c_double()
    k(
        dll.CC_GetMotorParamsExt,
        (
            sn,
            c.byref(spr),
            c.byref(gbr),
            c.byref(pitch)
        )
    )
    return spr.value, gbr.value, pitch.value

PRM1_Z8_SPR = 512
PRM1_Z8_GBR = 67
PRM1_Z8_PITCH = 17.8704

PRM1_Z7_SPR = 48
PRM1_Z7_GBR = 256
PRM1_Z7_PITCH = 18
def set_motor_params(
        sn,
        spr = PRM1_Z8_SPR,
        gbr = PRM1_Z8_GBR,
        pitch = PRM1_Z8_PITCH,
):
    sn, dll = sn
    return dll.CC_SetMotorParamsExt(
        sn,
        c.c_double(spr),
        c.c_double(gbr),
        c.c_double(pitch)
    )

def request_position(sn):
    sn, dll = sn
    k(
        dll.CC_RequestPosition,
        (sn,)
    )

def _get_position(sn):
    sn, dll = sn
    return dll.CC_GetPosition(sn)

def get_position_async(sn):        
    request_position(sn)
    yield from sleep(0.1)
    return _get_position(sn)

def get_position(sn):
    return get_blocking(get_position_async)(sn)

def get_angle(sn):
    return steps_to_angle(sn,get_position(sn))

def steps_to_angle(sn,steps):
    sn, dll = sn
    angle = c.c_double()
    k(
        dll.CC_GetRealValueFromDeviceUnit,
        (
            sn,
            steps,
            c.byref(angle),
            0
        )
    )
    return angle.value

def angle_to_steps(sn,angle):
    sn, dll = sn
    steps = c.c_int()
    dll.CC_GetDeviceUnitFromRealValue(
        sn,
        c.c_double(angle),
        c.byref(steps),
        0
    )
    return steps.value

def load_settings(sn):
    sn, dll = sn
    k(
        dll.CC_LoadSettings,
        (sn,),
        success=True
    )

def clear_message_queue(sn):
    sn, dll = sn
    dll.CC_ClearMessageQueue(sn)

def move_to_position(sn,steps):
    sn, dll = sn
    k(
        dll.CC_MoveToPosition,
        (
            sn,
            steps
        )
    )

# interval in milliseconds
def start_polling(sn,interval):
    sn, dll = sn
    k(
        dll.CC_StartPolling,
        (
            sn,
            interval
        ),
        success = True
    )

def stop_polling(sn):
    sn, dll = sn
    dll.CC_StopPolling(sn)

def reg_angle(angle):
    if angle < 0:
        angle += (int(abs(angle)/360) + 1)*360
    else:
        angle = angle % 360
    return angle

def check_for_messages(sn):
    sn, dll = sn
    return dll.CC_MessageQueueSize(sn)

def get_next_message(sn):
    sn, dll = sn
    mt = w.WORD()
    mid = w.WORD()
    md = w.DWORD()
    result = dll.CC_GetNextMessage(
        sn,
        c.byref(mt),
        c.byref(mid),
        c.byref(md),
    )    
    return result, (mt.value,mid.value,md.value)

def wait_for_message(sn):    
    sn, dll = sn
    mt = w.WORD()
    mid = w.WORD()
    md = w.DWORD()
    k(
        dll.CC_WaitForMessage,
        (
            sn,
            c.byref(mt),
            c.byref(mid),
            c.byref(md),
        ),
        success = True
    )
    return (mt.value,mid.value,md.value)

def match_message(msg,target_type,target_id):
    mt = msg[0]
    mid = msg[1]
    return mt == target_type and mid == target_id

def set_position(sn,position):
    yield from do_and_wait(
        sn,
        move_to_position,
        (
            sn,
            position
        ),
        M_GENERIC_MOTOR,
        M_MOVED        
    )

def set_angle_async(sn,angle):
    yield from set_position(sn,angle_to_steps(sn,angle))

def set_angle(sn,angle):
    return get_blocking(set_angle_async)(sn,angle)

S_HOMING = 9
S_HOMED = 10
def get_status_bits(sn):
    sn, dll = sn
    return w.DWORD(dll.CC_GetStatusBits(sn)).value

def request_status_bits(sn):
    sn, dll = sn
    k(
        dll.CC_RequestStatusBits,
        (sn,)
    )

def get_status(sn):
    request_status_bits(sn)
    return get_status_bits(sn)

def get_bit(num,nbit):
    return bool((num >> nbit) & 1)

def is_homed(sn):
    sbs = get_status(sn)
    return get_bit(sbs,S_HOMED)

def is_homing(sn):
    sbs = get_status(sn)
    return get_bit(sbs,S_HOMING)

def home_async(sn):
    sernum, dll = sn
    yield from do_and_wait(
        sn,
        k,
        (
            dll.CC_Home,
            (sernum,)
        ),
        M_GENERIC_MOTOR,
        M_HOMED        
    )

def home(sn):
    return get_blocking(home_async)(sn)

M_GENERIC_MOTOR = 2
M_MOVED = 1
M_HOMED = 0        
def do_and_wait(sn,f,args,target_type,target_id):    
    clear_message_queue(sn)
    result = f(*args)  
    yield  
    while True:        
        result, msg = get_next_message(sn)        
        if not result:
            yield
            continue
        if match_message(msg,target_type,target_id):
            break    
    return result

if __name__ == '__main__':
    import argparse    
    K = 'k'
    T = 't'
    ap = argparse.ArgumentParser(description='displays current position and prompts for new position')
    ap.add_argument('--cube','-c',choices=(K,T),default=K)
    typeid = {K:KCUBE_DC_SERVO,T:TCUBE_DC_SERVO}[ap.parse_args().cube]
    with RotationStageHandler(typeid=typeid) as sn:        
        sernum = sn[0]
        print('device sn: {}'.format(sernum.decode('utf8')))        
        while True:            
            print('current angle:','{:.3f}'.format(get_angle(sn)),'degrees')
            print(
                '\n'.join(
                    '\t{} : {}'.format(key,command) 
                    for key, command in (('s','set position'),('h','home motor'),('q','quit'))
                )
            )
            command = input('enter command: ')
            if not command: 
                print('invalid command')
                continue
            key = command[0]
            if key == 's':
                while True:
                    angle = input('enter new angle (or enter to abort): ')
                    if not angle:
                        break
                    try:
                        angle = float(angle)
                    except ValueError:
                        print('invalid angle (must be number)')
                        continue
                    if angle < -360 or angle > +360:
                        print('invalid angle (must be between -360 and 360)')
                        continue        
                    set_angle(sn,float(angle))
                    print('angle set.')
                    break
            elif key == 'h':
                print('homing...')
                home(sn)
                print('device homed')
            elif key == 'q':
                print('quitting.')
                break
            else:
                print('invalid command.')                