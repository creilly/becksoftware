import beckhttpclient as bhc

PORT = 8250
HOST = '127.0.0.1'

def argos_command(command,parameters):
    return bhc.send_command(HOST,PORT,command,parameters)

def get_wnum():
    return argos_command('get wnum',{})

print(get_wnum())
