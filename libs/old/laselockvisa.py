import pyvisa
from beckhttpserver import BeckError

llid = 'laselock'

A, B = 0, 1

X0, Y0, X1, Y1 = 0, 1, 2, 3

LOW_VOLTAGE, HIGH_VOLTAGE = 0, 1

LOW_MIN = -10.0
LOW_MAX = +10.0

calibs = {
    A:{
        X0:2.0, # volts
        Y0:90.3, # volts HV
        X1:-10.0, # volts
        Y1:-7.8 # volts
    },
    B:{
        X0:2.0, # volts
        Y0:89.9, # volts HV
        X1:-10.0, # volts
        Y1:-7.3 # volts
    },
}

# modes = {
#     A:LOW_VOLTAGE,
#     B:HIGH_VOLTAGE
# }

# deltas = {
#     A:-1,
#     B:5
# }

# ranges = {
#     A:(0.2,2.6),
#     B:(0,80)    
# }

modes = {
    A:LOW_VOLTAGE,
    B:LOW_VOLTAGE
}

deltas = {
    A:-1,
    B:-1
}

ranges = {
    A:(0.2,2.6),
    B:(-9,+9)    
}

regd = {
    A:'A',
    B:'B'
}

moded = {
    LOW_VOLTAGE:'V',
    HIGH_VOLTAGE:'HV'
}

def get_calib(reg):
    return map(
        calibs[reg].get,
        (X0, Y0, X1, Y1)
    )

def high_voltage_to_low_voltage(reg,hv):
    x0, y0, x1, y1 = get_calib(reg)
    return x0 + (hv - y0) * (x1 - x0) / (y1 - y0)

def low_voltage_to_high_voltage(reg,lv):
    x0, y0, x1, y1 = get_calib(reg)    
    return y0 + (lv - x0) * (y1 - y0) / (x1 - x0)

def low_voltage_to_percentage(lv):
    return 100 * lv / LOW_MAX

def open_ll():   
    ll = pyvisa.ResourceManager().open_resource(llid)
    ll.timeout = 250
    ll.write_termination = '\r'
    ll.read_termination = '\n'
    for reg in (A,B):
        delta = deltas[reg]
        if delta < 0:
            continue
        mode = modes[reg]
        if mode is HIGH_VOLTAGE:
            delta = (
                high_voltage_to_low_voltage(reg,delta)
                -
                high_voltage_to_low_voltage(reg,0)
            )
        percentage = low_voltage_to_percentage(delta)
        _set_reg_range(ll,reg,percentage)
    return ll

def close_ll(ll):
    ll.close()

def flush(ll):
    try:
        while True:
            ll.read()
    except pyvisa.errors.VisaIOError:
        return
    
def get_param(ll,param):
    flush(ll)
    return ll.query(param+'=').strip().split('=')[-1].strip()

def set_param(ll,param,value):
    flush(ll)
    return ll.query('= '.join((param,value))).strip().split('=')[-1].strip()

def _get_offset_param(reg):
    return 'RegOutOffset{}'.format(regd[reg])

# in volts
def get_reg_offset(ll,reg):
    offset = 1e-3*int(
        get_param(
            ll,
            _get_offset_param(reg)
        )
    )
    if modes[reg] is HIGH_VOLTAGE:
        offset = low_voltage_to_high_voltage(reg,offset)
    return offset

# in volts
def set_reg_offset(ll,reg,offset):
    vmin, vmax = ranges[reg]
    mode = modes[reg]
    if offset > vmax:
        raise BeckError(
            'requested offset ({0:f} {2}) greater than max offset ({1:f} {2})'.format(
                offset,
                vmax,
                moded[mode]
            )
        )
    if offset < vmin:
        raise BeckError(
            'requested offset ({0:f} {2}) less than min offset ({1:f} {2})'.format(
                offset,
                vmin,
                moded[mode]
            )
        )
    if modes[reg] is HIGH_VOLTAGE:
        offset = high_voltage_to_low_voltage(reg,offset)
    return set_param(
        ll,
        _get_offset_param(reg),
        str(round(1e3*offset))
    )

# in percentage of full range
def _set_reg_range(ll,reg,percentage):
    return set_param(
        ll,
        'RegOutRange{}'.format(regd[reg]),
        str(round(1e3*percentage))
    )

# import time
# N = 100
# ll = open_ll()
# tstart = time.time()
# for i in range(N):
#     if i % (N//10) == 0:
#         print(i,'\t/\t',N)
#     get_reg_offset(ll,A)
# print((time.time()-tstart)/N)
# close_ll(ll)
