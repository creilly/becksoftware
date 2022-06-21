import serial
import re
import json

llport = 'COM45'

write_term = '\r'
read_term = '\r\n'

chunk = 256

class LaseLockHandler:
    def __init__(self):
        self.ll = open_ll()

    def __enter__(self):
        return self.ll

    def __exit__(self,*args):
        close_ll(self.ll)

def open_ll():   
    ll = serial.Serial(llport,timeout=0.0)
    return ll

def close_ll(ll):
    ll.close()

def vardump(ll):
    write_ll(ll,'vardump')
    lr = LineReader(ll)
    vs = {}
    active = False
    done = False
    sep = '= '
    while True:
        resp = lr.read(chunk)
        line = lr.get_line()
        if line is not None:
            line = line.lower()
            if active:
                if 'end of list' in line:
                    done = True
                else:
                    key, value = [
                        f(s) for f, s in zip(
                            (str,int),line.split(sep)
                        )
                    ]
                    vs[key] = value
            else:
                if 'variables dump' in line:
                    active = True
            if not resp and done:
                return vs

def save_vars(fname,vs):
    with open(fname,'w') as f:
        f.write(
            json.dumps(
                vs,
                indent = 4
            )
        )

def load_vars(fname):
    with open(fname,'r') as f:
        return json.loads(f.read())

def write_vars(ll,vs):
    for key, value in vs.items():
        set_param(ll,key,value)

def write_ll(ll,command):
    ll.write(
        (
            command + write_term
        ).encode('utf8')
    )

class LineReader:
    def __init__(self,ll):
        self.ll = ll
        self.head = ''
        self.value = None

    def read(self,chunk):
        s = self.ll.read(chunk).decode()
        self.head += s
        return s

    def get_line(self):        
        if read_term in self.head:
            head, tail = self.head.split(read_term,1)
            self.head = tail
            return head
        else:
            return None

def _get_regex(param):
    return re.compile(r'^{}= (-?\d+)$'.format(param).lower())

def _get_param(ll,param):
    r = _get_regex(param)
    lr = LineReader(ll)
    value = None
    while True:
        resp = lr.read(chunk)
        line = lr.get_line()
        if line is not None:
            m = r.match(line.lower())
            if m:
                value = int(m.group(1))
        if not resp and value is not None:
            return value
    
def get_param(ll,param):
    write_ll(ll,param + '=')
    return _get_param(ll,param)

def set_param(ll,param,value):
    write_ll(ll,'{}= {:d}'.format(param.lower(),value))
    return _get_param(ll,param)

A, B = 0, 1

regd = {
    A:'A',
    B:'B'
}

def fmt_reg_param(p,reg):
    return '{}{}'.format(p,regd[reg])

frp = fmt_reg_param

# in volts
def get_reg_offset(ll,reg):
    offset = get_param(
        ll,
        frp('RegOutOffset',reg)
    )
    return offset / 1e3

# in volts
def set_reg_offset(ll,reg,offset):
    offset = set_param(
        ll,
        frp('RegOutOffset',reg),
        int(round(1e3*offset))
    )
    return offset / 1e3

# in percentage of full range
def _set_reg_range(ll,reg,percentage):
    return set_param(
        ll,
        'RegOutRange{}'.format(regd[reg]),
        round(1e3*percentage)
    )

# note here I use the more sensible convention of
# defining the "setpoint" to be the voltage that the
# regulator tries to lock on to, NOT (as LaseLock
# defines it) the voltage we subtract from the error
# signal and then always lock onto zero error signal.
# the two are of course related by a minus sign, as
# you can see from the code
# 
# setpoint is in volts
def set_reg_setpoint(ll,reg,setpoint):
    return set_param(
        ll,
        frp('RegSetPoint',reg),
        -int(1000*setpoint)
    )

def set_reg_on_off(ll,reg,enabled):
    return set_param(
        ll,
        frp('RegOnOff',reg),
        {
            True:1,False:0
        }[enabled]
    )

# ampl in volts
def set_li_ampl_aux(ll,ampl):
    return set_param(
        ll,
        'LIAmplAux',
        int(round(ampl*1e4))
    )

# returns dither monitor amplitude in volts
def get_li_ampl_aux(ll):
    return get_param(
        ll,
        'LIAmplAux'
    )*1e-4

if __name__ == '__main__':
    with LaseLockHandler() as llh:
        # print(get_reg_offset(llh,A))
        print(set_li_ampl_aux(llh,1.70))
        print(get_li_ampl_aux(llh))
        # vs = vardump(llh)
        # fname = 'piezo-dc.llv'
        # save_vars(fname,vs)
        # vps = load_vars(fname)        
        # for key in vs.keys():            
        #     print('param:',key,'v old:',vs[key],'v new:',vps[key])
        #     if vs[key] != vps[key]:
        #         print('mismatch')
        # write_vars(llh,vps)
        # print('A sp',get_param(llh,'RegSetPointA'))
        # set_reg_offset(llh,A,0.5)
        # print(get_reg_offset(llh,A))
