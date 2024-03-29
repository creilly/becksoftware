import pyvisa as visa
import ctypes

slope = 8.13211285167e-5 # measured 2022-07-20 # 0.00008145689 # 82.5e-6 # degrees per step

backlash = 13000 # steps (measured 2022-07-20)

MOTOR_NAME = 'lidmotor'
ADDRESS = 1
MOTOR = 0
TYPE = 0

class TrinamicError(Exception):
    def __init__(self,code):
        self.code = code
        super().__init__()

    def __str__(self):
        return 'error code {:d}: {}'.format(
            self.code,errord[self.code]
        )

    def __repr__(self):
        return str(self)

def get_crc(bytes):
    return sum(bytes) % 2**8

SUCCESS = 100
WRONG_CHECKSUM = 1
INVALID_COMMAND = 2
WRONG_TYPE = 3
INVALID_VALUE = 4
EEPROM_LOCKED = 5
COMMAND_NOT_AVAILABLE = 6

errord = {
    INVALID_COMMAND:'invalid command',
    WRONG_TYPE:'wrong type',
    INVALID_VALUE:'invalid value',
    COMMAND_NOT_AVAILABLE:'command not available',
}

GAP = 6
SAP = 5

ACT_POS = 1
TAR_POS = 0
POS_REACHED = 8
RLM_STATE, LLM_STATE = 10, 11
RLM_DISABLED, LLM_DISABLED = 12, 13

RIGHT, LEFT = 0, 1

MST = 3

MVP = 4
ABS, REL = 0, 1

SGP = 9
GGP = 10
STGP = 11

USER = 2

INITIALIZED = 0

PHI_MIN = 48
PHI_MAX = 60

ANGLE_LOW, ANGLE_OK, ANGLE_HIGH = 0, 1, 2
class InvalidAngleError(Exception):
    def __init__(self,angle_code,phi_req,phi_lim):
        self.angle_code = angle_code
        super().__init__(
            'requested angle {} degs {} than limit angle of {} degs.'.format(
                phi_req,
                {
                    ANGLE_LOW:'less',
                    ANGLE_HIGH:'greater'
                }[angle_code],
                phi_lim
            )
        )
class LidPositioner:    
    def __init__(self,lidmotor,phi_o,phi_min=PHI_MIN,phi_max=PHI_MAX):
        self.lidmotor = lidmotor
        self.phi_min = phi_min
        self.phi_max = phi_max
        self.calibrate_angle(phi_o)

    def calibrate_angle(self,phi_o):
        self.phi_o = phi_o
        self.pos_o = self.lidmotor.get_position()

    def get_angle(self):
        return self.phi_o + (
            self.lidmotor.get_position() - self.pos_o
        ) * slope

    def _get_position(self,phi):        
        pos = int(
            self.pos_o + ( phi - self.phi_o ) / slope
        )
        print('_get_position:','phi:',phi,'pos:',pos)
        return pos

    def set_phi_min(self,phi_min):
        self.phi_min = phi_min

    def set_phi_max(self,phi_max):
        self.phi_max = phi_max

    def get_phi_min(self):
        return self.phi_min
    
    def get_phi_max(self):
        return self.phi_max    

    def _set_angle(self,phi): 
        if phi < self.phi_min:
            raise InvalidAngleError(ANGLE_LOW,phi,self.phi_min)
        if phi > self.phi_max:
            raise InvalidAngleError(ANGLE_HIGH,phi,self.phi_max)
        self.lidmotor.set_position(
            self._get_position(phi)
        )

    # always blocks on negative moves
    # def set_angle(self,phi,wait=True):
    #     dphi = phi - self.get_angle()
    #     if dphi < 0:
    #         print('negative move requested! backlash compensating...')
    #         phi_bl = phi - self.get_backlash()
    #         self._set_angle(phi_bl)            
    #         self.wait()
    #         print('backlash compensation complete')
    #     print('going forward to requested angle.')
    #     self._set_angle(phi)    
    #     if wait:
    #         self.wait()
    #         print('done.')

    def set_angle(self,phi,wait=True):        
        self._set_angle(phi)    
        if wait:
            self.wait()            

    def wait(self):
        self.lidmotor.wait()
        
    @staticmethod
    def get_backlash():
        return abs(backlash * slope)

class LidMotor:
    def __init__(self,motor):
        self.motor = motor

    def send_command(self,command,type=0,data=0,bank=MOTOR):
        command = [ADDRESS,command,type,bank] + self.uint32_to_bytes(
            self.int32_to_uint32(
                data
            )
        )
        command.append(get_crc(command))
        while True:
            self.motor.write_raw(bytes(command))
            response = self.motor.read_bytes(9)
            response, crc = response[:8], response[8]
            if crc != get_crc(response):
                continue
            status = response[2]
            if status == SUCCESS:
                break
            if status == WRONG_CHECKSUM:
                continue
            raise TrinamicError(status)
        data = response[4:8]
        return self.uint32_to_int32(self.bytes_to_uint32(data))

    @staticmethod
    def int32_to_uint32(int32):
        return ctypes.c_uint32(int32).value

    @staticmethod
    def uint32_to_int32(uint32):
        return ctypes.c_int32(uint32).value

    @staticmethod
    def uint32_to_bytes(uint32):
        return [
            uint32>>8*n&(1<<8)-1 for n in range(4)[::-1]
        ]

    @staticmethod
    def bytes_to_uint32(bytes):
        return sum(b<<8*n for n, b in enumerate(bytes[::-1]))

    def get_axis_param(self,param):
        return self.send_command(GAP,param)

    def set_axis_param(self,param,data):
        return self.send_command(SAP,param,data)

    def get_global_parameter(self,bank,param):
        return self.send_command(
            GGP,
            param,
            bank=USER
        )

    def set_global_parameter(self,bank,param,value):
        return self.send_command(
            SGP,
            param,
            value,
            bank=bank,            
        )

    def store_global_parameter(self,bank,param,value):
        return self.send_command(
            STGP,
            param,
            value,
            bank=bank,            
        )

    def get_user_parameter(self,param):
        return self.get_global_parameter(
            USER,
            param
        )

    def store_user_parameter(self,param,value):
        return self.store_global_parameter(
            USER,
            param,
            value,
        )

    def set_user_parameter(self,param,value):
        return self.set_global_parameter(
            USER,
            param,
            value,
        )

    def initialized(self):
        return bool(self.get_user_parameter(INITIALIZED))

    def initialize(self,initialized=True):
        self.set_user_parameter(INITIALIZED,int(initialized))

    def get_position(self):
        return self.get_axis_param(ACT_POS)

    def get_target_position(self):
        return self.get_axis_param(TAR_POS)

    def get_limit_switch_disabled(self,edge):
        return bool(
            self.get_axis_param(
                {
                    RIGHT:RLM_DISABLED,
                    LEFT:LLM_DISABLED
                }[edge]
            )
        )

    def set_limit_switch_disabled(self,edge,disabled):
        self.set_axis_param(
            {
                RIGHT:RLM_DISABLED,
                LEFT:LLM_DISABLED
            }[edge],
            int(disabled)
        )

    def get_limit_switch_state(self,edge):
        return bool(
            self.get_axis_param(
                {
                    RIGHT:RLM_STATE,
                    LEFT:LLM_STATE
                }[edge]
            )
        )
    
    def position_reached(self):
        return bool(
            self.get_axis_param(
                POS_REACHED
            )
        )

    def set_reference_position(self,position):
        self.set_axis_param(
            ACT_POS,
            position
        )

    def set_position(self,position):
        self.send_command(
            MVP,
            ABS,
            position
        )

    def set_relative_position(self,displacement):
        self.send_command(
            MVP,
            REL,
            displacement
        )

    def stop_motor(self):
        self.send_command(MST)

    def wait(self,cb=None):
        while not self.position_reached():
            if cb is not None:
                cb()
    
class LidMotorHandler:
    def __init__(self,motor_name=MOTOR_NAME):
        self.motor_name = motor_name
        self.resource = None

    def __enter__(self):
        self.resource = visa.ResourceManager().open_resource(
            self.motor_name
        )
        return LidMotor(self.resource)

    def __exit__(self,*args):
        if self.resource is not None:
            self.resource.close()    

if __name__ == '__main__':
    with LidMotorHandler() as motor:
        while True:
            phi_o = float(input('enter current angle (in degrees): '))            
            lp = LidPositioner(motor,phi_o)
            phi_p = input('enter desired angle (in degrees, or enter to quit): ')
            if phi_p:
                lp.set_angle(float(phi_p))
                continue
            break
            
