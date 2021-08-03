import serial

qubigid = 'COM3'

qubig = serial.Serial('COM3',xonxoff=1)

termseq = '\r\n'

msgtermseq = '>>> '

def get_status():
    rawstatus = send_command('driver_info()')
    categories = {}
    category = None
    for line in rawstatus.split('\n'):
        if line[0] != ' ':
            category = line.split(':')[0]
            properties = {}
            categories[category] = properties
        else:
            property, value = map(str.strip,line.strip().split('='))
            properties[property] = value
    return categories

def get_qlock_status():
    return get_status()['state - locking']['Enabled']
    
def read_response():
    return qubig.read_until(msgtermseq.encode())[:-len(msgtermseq)].decode('utf-8').strip()

def send_command(command):
    qubig.write(
        (
            command + termseq
        ).encode()
    )
    return read_response()

def get_lock():
    send_command('start_lock()')
    while {
            'scanning':True,
            'r-lock':False
    }[get_qlock_status()]:
        continue
    
def set_frequency(frequency):
    send_command('set_frequency({:f})'.format(frequency))

def set_power(power):
    send_command('set_power({:f})'.format(power))

def get_temperature():
    return float(get_status()['state - t-control']['Temperature'].split(' ')[0])

