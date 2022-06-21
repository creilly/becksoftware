import pyvisa
from pyvisa import constants

FL = 'fl'
HV = 'hv'
DG = 'dg'

readterm = b'\n'
writeterm = b'\r'
ack = b'\06'
enq = b'\05'
etx = b'\03'

ayt = b'AYT'
bau = b'BAU'
pr = b'PR'
prx = b'PRX'
eth = b'ETH'


visaids = {
    FL:'maxigaugeforeline',
    HV:'maxigaugehv',
    DG:'heliumpressure'
}

class PfeifferGaugeHandler:
    def __init__(self,visaid,timeout=1000):
        self.visaid = visaid
        self.timeout = timeout

    def __enter__(self):
        self.handle = open_gauge(self.visaid,self.timeout)        
        return self.handle

    def __exit__(self,*args):
        close_gauge(self.handle)

def open_gauge(visaid,timeout=100):
    inst = pyvisa.ResourceManager().open_resource(visaid,open_timeout=timeout)        
    inst.read_termination = '\n'
    inst.timeout = 0
    while True:
        try:        
            inst.read()
        except Exception:            
            break
    inst.timeout = timeout
    return inst

def close_gauge(handle):
    handle.close()

def read_response(handle):
    resp = b''
    while True:
        b = handle.read_bytes(1)
        resp += b        
        if b == readterm:
            break
    return resp

def send_command(handle,command):
    handle.write_raw(command+writeterm)
    read_response(handle)    
    handle.write_raw(enq)
    return read_response(handle).decode('utf8').strip()

def are_you_there(handle):
    return send_command(handle,ayt)

def baud_rate(handle):
    return send_command(handle,bau)

def get_pressure(handle,gaugenumber):
    return float(send_command(handle,pr + str(gaugenumber).encode()).split(',')[1])
class PfeifferError(Exception):
    pass
def get_pressures(handle):
    fields = send_command(handle,prx).split(',')    
    pressures = []
    while fields:
        fields.pop(0) # discard status
        if not fields:
            raise PfeifferError(
                'pressure data not of form ...,status,pressure,...'
            )
        pressures.append(float(fields.pop(0)))
    return pressures

STATIC = 0
DYNAMIC = 1
DHCP = DYNAMIC
def configure_ethernet(handle,ip,mask,gateway):
    return send_command(
        handle,
        b' '.join(
            [
                eth,
                ','.join([str(DHCP),ip,mask,gateway]).encode()
            ]
        )
    )

if __name__ == '__main__':
    # inst = pyvisa.ResourceManager().open_resource('maxigaugehv')
    # try:
    #     inst.write_raw('AYT\r'.encode())
    #     resp = b''
    #     n = 0
    #     while n < 3:
    #         resp += inst.read_bytes(1)
    #         print('resp:',resp)
    #         n += 1        
    #     inst.write_raw(b'\05')
    #     n = 0
    #     resp = b''
    #     while n < 50:
    #         b = inst.read_bytes(1)
    #         resp += b
    #         print('resp:',resp)
    #         n += 1      
    #         if b == b'\n':
    #             break
    # finally:
    #     inst.close()
    # exit()
    import argparse
    parser = argparse.ArgumentParser(description='pfeiffer gauge controller')
    parser.add_argument(
        'gauge',choices=(FL,HV,DG)
    )
    gauge = parser.parse_args().gauge
    visaid = visaids[gauge]
    with PfeifferGaugeHandler(visaid) as mgh:
        print(are_you_there(mgh))
        print(baud_rate(mgh))
        print(get_pressure(mgh,1))
        print(get_pressures(mgh))
        # print(configure_ethernet(mgh,'192.168.1.36','255.255.255.0','192.168.1.1'))

