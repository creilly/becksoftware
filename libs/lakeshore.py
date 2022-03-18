import pyvisa
from time import time

VISAID = 'lakeshore'

readterm = writeterm = '\r\n'

waittime = 100e-3 # seconds

class LakeShoreMonitorHandler:
    def __init__(self,visaid=VISAID):
        self.visaid = visaid
        self.start = time()

    def send_message(self,message):
        while time() - self.start < waittime:
            continue
        self.handle.write(message)
        response = self.handle.read()
        self.start = time()
        return response

    def __enter__(self):
        self.handle = open_monitor(self.visaid)
        return self

    def __exit__(self,*args):
        close_monitor(self.handle)

    def identify(self):
        return self.send_message('*IDN?')

    # in kelvin
    def get_temperature(self):
        return float(self.send_message('KRDG?'))

def open_monitor(visaid=VISAID):
    handle = pyvisa.ResourceManager().open_resource(visaid)
    handle.baud_rate = 9600
    handle.data_bits = 7
    handle.parity = 1
    handle.timeout = 100
    handle.read_termination = readterm
    handle.write_termination = writeterm
    return handle

def close_monitor(handle):
    handle.close()

if __name__ == '__main__':
    with LakeShoreMonitorHandler() as lsm:
        print('temperature:',lsm.get_temperature(),'kelvin')