import pyvisa as visa

visaname = 'piezo'

channel = 'x'

termchar = '\r'

class PiezoDriverHandler():
    def __init__(self):
        self.pdh = pdh = open_piezo_driver()
        pdh.read_termination = pdh.write_termination = termchar        

    def __enter__(self):
        return self.pdh

    def __exit__(self,*args):
        close_piezo_driver(self.pdh)

def write(pdh,param,value):
    pdh.write('{}={}'.format(param,value))
    return pdh.read_bytes(1).decode('utf8')

def query(pdh,param):
    return pdh.query('{}?'.format(param)).split('*')[-1]

def open_piezo_driver():
    return visa.ResourceManager().open_resource(visaname)

def close_piezo_driver(pdh):
    pdh.close()

def set_piezo_voltage(pdh,voltage,channel=channel):
    return write(pdh,'{}voltage'.format(channel),'{:.4f}'.format(voltage))

def get_piezo_voltage_act(pdh,channel=channel):
    return float(
        query(
            pdh,'{}voltage'.format(channel)
        ).split('[')[-1].split(']')[0]
    )

get_piezo_voltage = get_piezo_voltage_act

def set_rotary_push(pdh,disabled):
    return write(
        pdh,
        'disablepush',
        str(int(disabled))
    )

def get_rotary_push(pdh):
    return query(
        pdh,
        'disablepush'
    )

def get_rotary_mode(pdh):
    return query(pdh,'rotarymode?')

DEF, TEN, FIN = 0, 1, 2
def set_rotary_mode(pdh,mode):
    return write(pdh,'rotarymode',str(mode))

if __name__ == '__main__':
    with PiezoDriverHandler() as pdh:
        # pdh.write('?')
        # try:
        #     while True:
        #         print(pdh.read())
        # except Exception:
        #     pass
        # set_rotary_mode(pdh,FIN)
        # print('rotary mode?',get_rotary_mode(pdh))
        # for _ in range(10):
        #     print(set_rotary_mode(pdh,TEN))
        # print('rotary mode?',get_rotary_mode(pdh))
        # vo = get_piezo_voltage_act(pdh)
        # print('vo,',vo)
        vp = float(input('set piezo voltage to: '))
        print(set_piezo_voltage(pdh,vp))
        vpp = get_piezo_voltage_act(pdh)
        print('vpp,',vpp)

    
