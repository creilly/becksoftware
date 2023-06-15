import lid
import beckhttpclient as bhc

HOST = bhc.get_host()
PORT = lid.PORT

def send_command(command,parameters={}):
    return bhc.send_command(HOST,PORT,command,parameters) 

def calibrate_lid(phi_o):
    return send_command('calibrate-lid',{'phi_o':phi_o})

def set_lid(phi,wait=True):
    send_command('set-lid',{'phi':float(phi)})
    if wait:
        while get_moving():
            continue

def get_lid():
    return send_command('get-lid')

def get_encoder():
    return send_command('get-encoder')

def get_moving():
    return send_command('get-moving')

def wait_lid(hook=None):
    while get_moving():
        if hook is not None:
            hook()

def get_phi_min():
    return send_command('get-phi-min')

def get_phi_max():
    return send_command('get-phi-max')

def set_phi_min(phi_min):
    return send_command('set-phi-min',{'phi_min':phi_min})

def set_phi_max(phi_max):
    return send_command('set-phi-max',{'phi_max':phi_max})

if __name__ == '__main__':
    print('lid angle:',get_lid())