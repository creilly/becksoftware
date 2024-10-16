import beckhttpclient as bhc, base64, struct
from tc import tcserver as tcs, PORT

host = '127.0.0.1'
port = PORT

epsilonfo = 0.5 # MHz

D = 'direction'

def send_command(command,params={}):
    return bhc.send_command(host,port,command,params)

def get_lock_output(d):
    return send_command('get lock output',{D:d})

def get_setpoint(d):
    return send_command('get setpoint',{D:d})

def set_setpoint(d,setpoint,wait=True,epsilonf=epsilonfo):
    send_command('set setpoint',{D:d,'setpoint':setpoint})    
    if wait:
        check_transfer_cavity(d,setpoint,epsilonf)

def get_locking(d):
    return send_command('get locking',{D:d})

def set_locking(d,locking):
    return send_command('set locking',{D:d,'locking':locking})

def zero_offset(d):
    return send_command('zero offset',{D:d})

def get_scanning():
    return send_command('get scanning')

def set_scanning(scanning):
    return send_command('set scanning',{'scanning':scanning})

def get_scan_index(d):
    return send_command('get scan index',{D:d})

def get_scan(d,decimated):
    response = send_command(
        'get scan',{D:d,'decimated':decimated}
    )
    if response is None: return None
    index, scand = response
    return index, {
        channel:{
            tcs.SCAN:decode_scan(channeld[tcs.SCAN]),
            tcs.FIT:channeld[tcs.FIT]
        }
        for channel, channeld in scand.items()
    }

def get_x(d,decimated):
    return decode_scan(send_command('get x',{D:d,'decimated':decimated}))

def get_fitting(d):
    return send_command('get fitting',{D:d})

def set_fitting(d,fitting):
    return send_command('set fitting',{D:d,'fitting':fitting})

def decode_scan(b64scan):
    bs = base64.b64decode(b64scan.encode())
    return struct.unpack(
        '{:d}f'.format(len(bs)//4),
        bs
    )

def get_frequency(d):
    return send_command('get frequency',{D:d})

def get_frequencies(d,index):
    return send_command('get frequencies',{D:d,'index':index})

def get_frequencies_index(d):
    return send_command('get frequencies index',{D:d})

def get_frequency_modulation_mode():
    return send_command('get frequency modulation mode')

def check_transfer_cavity(d,fset,epsilonf=epsilonfo):
    scan_index = get_scan_index(d)
    while True:
        samples = get_frequencies(d,scan_index)
        if samples:
            for f in samples:
                scan_index += 1                
                if abs(f-fset) < epsilonf:                    
                    return True                