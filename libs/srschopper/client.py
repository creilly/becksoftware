import beckhttpclient as bhc
from srschopper import PORT

host = '127.0.0.1'
port = PORT

def send_command(command,params={}):
    return bhc.send_command(host,port,command,params)

def get_delay():
    return send_command('get delay')

def get_control():
    return send_command('get control')

def set_control(control):
    return send_command('set control',{'control':control})

def get_locking():
    return send_command('get locking')

def set_locking(locking):
    return send_command('set locking',{'locking':locking})

def get_setpoint():
    return send_command('get setpoint')

def set_setpoint(setpoint):
    return send_command('set setpoint',{'setpoint':setpoint})

if __name__ == '__main__':
    # set_locking(True)
    # exit()
    spo = get_setpoint()
    print('current setpoint:',1e3 * round(spo,3),'ms')
    spp = float(input('enter new setpoint (ms): ')) / 1e3
    set_setpoint(spp)