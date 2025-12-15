import beckhttpclient as bhc
from alerter import PORT

host = '127.0.0.1'
port = PORT

def send_command(command,params={}):
    return bhc.send_command(host,port,command,params)

def get_alert():
    return send_command('get alert')

def set_alert(alert):
    return send_command('set alert',{'alert':alert})

def clear_alert():
    return send_command('clear alert')