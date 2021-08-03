import pyvisa

pmid = 'powermeter'
pm = pyvisa.ResourceManager().open_resource(pmid)

def get_power():
    return float(pm.query('READ?'))

def get_idn():
    return pm.query('*IDN?')

if __name__ == '__main__':
    print('idn',get_idn())
    print('power',get_power())
# # dll module
# from ctypes import *

# tlpmid = b'USB0::0x1313::0x807C::1909288::INSTR'
# tlpm = TLPM()
# tlpm.open(create_string_buffer(tlpmid), c_bool(True), c_bool(True))

# def get_power():
#     power = c_double()
#     tlpm.measPower(byref(power))
#     return power.value

