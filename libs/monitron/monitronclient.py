import bologain
import beckhttpclient as bhc

HOST = bhc.get_host()
PORT = bologain.PORT

def send_command(command,parameters={}):
    return bhc.send_command(HOST,PORT,command,parameters) 

def set_gain(gain):
    return send_command('set-gain',{'gain':gain})

def get_gain():
    return send_command('get-gain')

if __name__ == '__main__':
    print('gain?',get_gain())