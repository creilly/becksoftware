import beckhttpclient as bhc

port = 8999
host = '127.0.0.1'

def send_command(command,parameters):
    return bhc.send_command(host,port,command,parameters)

sc = send_command

def get_locking():
    return sc('get-locking',{})

def set_locking(locking):
    return sc('set-locking',{'locking':locking})

def get_wavenumber_set():
    return sc('get-wavenumber-set',{})

def get_wavenumber_act():
    return sc('get-wavenumber-act',{})

def set_wavenumber(wavenumber):
    return sc('set-wavenumber',{'wavenumber':wavenumber})

def get_damping():
    return sc('get-damping',{})

def set_damping(damping):
    return sc('set-damping',{'damping':damping})
