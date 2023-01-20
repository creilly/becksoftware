import pyvisa

PORT = 8010

VISAID = 'bologain'
FLOW_CONTROL = pyvisa.constants.ControlFlow.dtr_dsr

X10 = 10
X100 = 100
X200 = 200
X1000 = 1000

gains = (X10,X100,X200,X1000)

char_d = {
    X10:b'0',X100:b'1',X200:b'2',X1000:b'3'
}

class BoloGainHandler():
    def __enter__(self):
        self.handle = open_bologain()
        return self.handle

    def __exit__(self,*args):
        close_bologain(self.handle)

def open_bologain():
    return pyvisa.ResourceManager().open_resource(VISAID,flow_control=FLOW_CONTROL)

def set_gain(handle,gain):
    handle.write_raw(char_d[gain])

def close_bologain(handle):
    handle.close()