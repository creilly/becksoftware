import ctypes as c
import ctypes.wintypes as w
from beckutil import load_dll
from time import sleep

class RotationStageHandler:
    def __init__(self,sn=None):
        self.sn = open_device(sn)

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

dllname = r'Thorlabs.MotionControl.KCube.DCServo.dll'

dll = load_dll(dllname)

TCUBE_DC_SERVO = 83
KCUBE_DC_SERVO = 27
def list_devices(typeid = KCUBE_DC_SERVO):
    k(
        dll.TLI_BuildDeviceList,
        ()
    )
    
    ndevs = dll.TLI_GetDeviceListSize()

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

def open_device(sn = None):
    if sn is None:
        sns = list_devices()
        if not sns:
            raise Exception('no devices connected')
        sn = sns[0]
    k(
        dll.CC_Open,
        (sn,)
    )
    load_settings(sn)
    return sn

def close_device(sn):
    dll.CC_Close(sn)

def get_motor_params(sn):
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
def set_motor_params(
        sn,
        spr = PRM1_Z8_SPR,
        gbr = PRM1_Z8_GBR,
        pitch = PRM1_Z8_PITCH,
):
    return dll.CC_SetMotorParamsExt(
        sn,
        c.c_double(spr),
        c.c_double(gbr),
        c.c_double(pitch)
    )

def request_position(sn):
    k(
        dll.CC_RequestPosition,
        (sn,)
    )

def get_position(sn):
    return dll.CC_GetPosition(sn)

def get_angle(sn):
    request_position(sn)    
    return steps_to_angle(
        sn,
        get_position(sn)
    )

def steps_to_angle(sn,steps):
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
    steps = c.c_int()
    dll.CC_GetDeviceUnitFromRealValue(
        sn,
        c.c_double(angle),
        c.byref(steps),
        0
    )
    return steps.value

def load_settings(sn):
    k(
        dll.CC_LoadSettings,
        (sn,),
        success=True
    )

def clear_message_queue(sn):
    dll.CC_ClearMessageQueue(sn)

def move_to_position(sn,steps):
    k(
        dll.CC_MoveToPosition,
        (
            sn,
            steps
        )
    )

# interval in milliseconds
def start_polling(sn,interval):
    k(
        dll.CC_StartPolling,
        (
            sn,
            interval
        ),
        success = True
    )

def stop_polling(sn):
    dll.CC_StopPolling(sn)

def reg_angle(angle):
    if angle < 0:
        angle += (int(abs(angle)/360) + 1)*360
    else:
        angle = angle % 360
    return angle

def wait_for_message(sn):
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

def set_angle(sn,angle):
    do_and_wait(
        sn,
        move_to_position,
        (
            sn,
            angle_to_steps(sn,angle)
        ),
        M_GENERIC_MOTOR,
        M_MOVED,
        100
    )

S_HOMING = 9
S_HOMED = 10
def get_status_bits(sn):
    return w.DWORD(dll.CC_GetStatusBits(sn)).value

def request_status_bits(sn):
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

def home(sn):
    do_and_wait(
        sn,
        k,
        (
            dll.CC_Home,
            (sn,)
        ),
        M_GENERIC_MOTOR,
        M_HOMED,
        100
    )

M_GENERIC_MOTOR = 2
M_MOVED = 1
M_HOMED = 0        
def do_and_wait(sn,f,args,target_type,target_id,interval):
    start_polling(sn,interval)
    clear_message_queue(sn)
    result = f(*args)
    while True:
        msg = wait_for_message(sn)
        if match_message(msg,target_type,target_id):
            break
    stop_polling(sn)
    return result

if __name__ == '__main__':
    with RotationStageHandler() as sn:
        print('angle:','{:.3f}'.format(get_angle(sn)),'degrees')
