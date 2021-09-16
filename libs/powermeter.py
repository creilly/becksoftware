import pyvisa

pmid = 'powermeter'
pm = pyvisa.ResourceManager().open_resource(pmid)

def open_pm(pmid=pmid):
    return pyvisa.ResourceManager().open_resource(pmid)

def get_power(pm):
    return float(pm.query('READ?'))

def get_idn(pm):
    return pm.query('*IDN?')

def close_pm(pm):
    pm.close()

if __name__ == '__main__':
    pm = open_pm()
    # print(pm.write('CONF:POW'))
    print('conf',pm.query('CONF?'))
    print('idn',get_idn(pm))
    print('power',get_power(pm))
    close_pm(pm)
# # dll module
# from ctypes import *

# tlpmid = b'USB0::0x1313::0x807C::1909288::INSTR'
# tlpm = TLPM()
# tlpm.open(create_string_buffer(tlpmid), c_bool(True), c_bool(True))

# def get_power():
#     power = c_double()
#     tlpm.measPower(byref(power))
#     return power.value

