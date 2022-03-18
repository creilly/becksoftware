import pyvisa as visa

# all powers are measured in watts

visaid = 'ipg-argos-c1'

termchar = '\r'

sepchar = ':'

BCMD = 'BMCD'

EMISSION = 0
STARTUP = 1
BACKREFLECTION = 17

statusbits = (EMISSION,STARTUP,BACKREFLECTION)

ON = 'On'
OFF = 'Off'

class IPGHandler:
    def __init__(self,visaid=visaid):
        self.visaid = visaid

    def __enter__(self):
        self.ipgh = open(visaid)
        return self.ipgh

    def __exit__(self,*args):
        close(self.ipgh)

class IPGError(Exception):
    pass

def send_command(ipgh,command,param=None):
    if param is None:
        commandstr = command
    else:
        commandstr = '{} {}'.format(command,param)
    response = ipgh.query(commandstr)
    if sepchar in response:
        echo, value = response.split(sepchar,1)
        value = value.strip()
    else:
        echo = response
        value = None
    if echo == BCMD:
        raise IPGError('bad command')
    elif echo != command.upper():
        raise IPGError('echoed command "{}" does not match issued command "{}"'.format(command.upper(),echo))
    return value    

def open(visaid=visaid):
    ipgh = visa.ResourceManager().open_resource(visaid)
    ipgh.write_termination = ipgh.read_termination = termchar
    return ipgh

def close(ipgh):
    ipgh.close()

def get_status(ipgh):
    status_value = int(send_command(ipgh,'STA'))
    return {
        bit:bool((status_value//2**bit)%2)
        for bit in statusbits
    }

def get_emission_state(ipgh):
    emission_str = send_command(ipgh,'REM')
    return {
        key.lower():state
        for key, state in ((ON,True),(OFF,False))
    }[emission_str.lower()]

def set_emission_state(ipgh,state):
    return send_command(
        ipgh,{
            True:'EMON',
            False:'EMOFF'
        }[state]
    )

POWER, CURRENT = 0, 1
def set_control_mode(ipgh,mode):
    return send_command(
        ipgh,{
            POWER:'APC',
            CURRENT:'ACC'
        }
    )

def get_power_setpoint(ipgh):
    return float(send_command(ipgh,'RPS'))

def set_power_setpoint(ipgh,power):
    send_command(ipgh,'SPS',str(power))

def get_output_power(ipgh):
    return float(send_command(ipgh,'ROP'))

def get_input_power(ipgh):
    return 1e-3*float(send_command(ipgh,'RIN'))

if __name__ == '__main__':
    with IPGHandler() as ipgh:
        print('status',get_status(ipgh))
        print('emission state',get_emission_state(ipgh))
        print('power setpoint',get_power_setpoint(ipgh))
        print('output power',get_output_power(ipgh))
        print('input power',get_input_power(ipgh))
        
