import serial
import re

llport = 'com7'

write_term = '\r'
read_term = '\r\n'

chunk = 256

def open_ll():   
    ll = serial.Serial(llport)
    ll.timeout = 0
    return ll

def close_ll(ll):
    ll.close()

def _get_regex(param):
    return re.compile(r'^{}= (-?\d+)$'.format(param).lower())

def _get_param(ll,param):
    r = _get_regex(param)
    head = ''
    value = None
    i = 0
    while True:
        i += 1
        resp = ll.read(chunk).decode()
        head += resp
        while read_term in head:
            head, tail = head.split(read_term,1)
            m = r.match(head.lower())
            if m:
                value = int(m.group(1))
            head = tail
        if not resp and value is not None:
            return value
    
def get_param(ll,param):    
    ll.write(
        (
            param.lower() + '=' + write_term
        ).encode('utf8')
    )
    return _get_param(ll,param)

def set_param(ll,param,value):
    ll.write(
        (
            '{}= {:d}'.format(param.lower(),value)
            +
            write_term
        ).encode('utf8')
    )
    return _get_param(ll,param)

A, B = 0, 1

X0, Y0, X1, Y1 = 0, 1, 2, 3

LOW_VOLTAGE, HIGH_VOLTAGE = 0, 1

modes = {
    A:LOW_VOLTAGE,
    B:LOW_VOLTAGE
}

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

# high voltage B settings vvvvv

deltas = {
    A:-1,
    B:{
        HIGH_VOLTAGE:5,
        LOW_VOLTAGE:-1
    }[modes[B]]
}

ranges = {
    A:(0.2,2.6),
    B:{        
        HIGH_VOLTAGE:(-5,+80),
        LOW_VOLTAGE:(-9,+9)        
    }[modes[B]]
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

def _get_offset_param(reg):
    return 'RegOutOffset{}'.format(regd[reg])

# in volts
def get_reg_offset(ll,reg):
    offset = 1e-3*get_param(
        ll,
        _get_offset_param(reg)
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
    offset = 1e-3*set_param(
        ll,
        _get_offset_param(reg),
        round(1e3*offset)
    )
    if modes[reg] is HIGH_VOLTAGE:
        offset = low_voltage_to_high_voltage(reg,offset)
    return offset

# in percentage of full range
def _set_reg_range(ll,reg,percentage):
    return set_param(
        ll,
        'RegOutRange{}'.format(regd[reg]),
        round(1e3*percentage)
    )

# ll = open_ll()

# ll.write('Hello\r'.encode('utf8'))

# print(get_reg_offset(ll,B))
# print(set_reg_offset(ll,B,40.0))

# close_ll(ll)

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
