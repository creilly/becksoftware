import pyvisa

FL = 'fl'
HV = 'hv'
DG = 'dg'

readterm = b'\n'
writeterm = b'\r'
ack = b'\06'
enq = b'\05'

ayt = b'AYT'
bau = b'BAU'
pr = b'PR'
prx = b'PRX'

visaids = {
    FL:'maxigaugeforeline',
    HV:'maxigaugehighvacuum',
    DG:'heliumpressure'
}

class PfeifferGaugeHandler:
    def __init__(self,visaid,timeout=100):
        self.visaid = visaid
        self.timeout = timeout

    def __enter__(self):
        self.handle = open_gauge(self.visaid,self.timeout)
        self.handle.readtermination = readterm
        return self.handle

    def __exit__(self,*args):
        close_gauge(self.handle)

def open_gauge(visaid,timeout=100):
    return pyvisa.ResourceManager().open_resource(visaid,open_timeout=timeout)

def close_gauge(handle):
    handle.close()

def send_command(handle,command):
    handle.write_raw(command+writeterm)
    handle.read_raw()
    handle.write_raw(enq)
    return handle.read_raw().decode('utf8').strip()

def are_you_there(handle):
    return send_command(handle,ayt)

def baud_rate(handle):
    return send_command(handle,bau)

def get_pressure(handle,gaugenumber):
    return float(send_command(handle,pr + str(gaugenumber).encode()).split(',')[1])

def get_pressures(handle):
    fields = send_command(handle,prx).split(',')
    pressures = []
    while fields:
        fields.pop(0) # discard status
        pressures.append(float(fields.pop(0)))
    return pressures

if __name__ == '__main__':
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

