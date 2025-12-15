import beckhttpclient as bhc
from shs import PORT

host = '127.0.0.1'
port = PORT

def send_command(command,params={}):
    return bhc.send_command(host,port,command,params)

def get_temperature():
    return send_command('get temperature')

def get_ev_sp():
    return send_command('get ev sp')

def set_ev_sp(ev):
    return send_command('set ev sp',{'ev':int(round(ev))})

def get_ec():
    return send_command('get ec')

def reconnect_topo():
    return send_command('reconnect topo')

def get_heating_mode():
    return send_command('get heating mode')

def get_cc_sp():
    return send_command('get cc sp')

def set_cc_sp(cc):
    return send_command('set cc sp',{'cc':cc})

def get_operation_mode():
    return send_command('get operation mode')

def get_cc():
    return send_command('get cc')

def get_ev():
    return send_command('get ev')

def get_cv():
    return send_command('get cv')

if __name__ == '__main__':
    pass  