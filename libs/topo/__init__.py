import socket as s
import re

IP = '10.10.10.10'
commandport = 1998
monitoringport = 1999

writeterm = '\n'
commandreadterm = '\n' + '> '
monitoringreadterm = '\n'

bufsize = 256

class Client:
    def __init__(self,port,readterm):
        socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        socket.connect((IP,port))
        self.socket = socket
        self.readterm = readterm
        
    def write(self,msg):
        msg += writeterm
        msg = msg.encode()
        self.socket.sendall(msg)

    def send_command(self,command):
        self.write(command)
        return self.read()

STR, INT, FLOAT, BOOL = 0, 1, 2, 3
def format_value(value,mode):
    if mode is STR:
        return '"{}"'.format(value)
    if mode is INT:
        return str(value)
    if mode is FLOAT:
        return str(value)
    if mode is BOOL:
        return '#' + {True:'t',False:'f'}[value]

def parse_value(value,mode):
    if mode is STR:
        return value[1:-1]
    if mode is INT:
        return int(value)
    if mode is FLOAT:
        return float(value)
    if mode is BOOL:
        return {'t':True,'f':False}[value[1]]

def format_command(command,*parameters):
    return '({})'.format(
        ' '.join([command] + list(parameters))
    )

def format_param(param):
    return '\'{}'.format(param)
        
class CommandClient(Client):
    def __init__(self):
        super().__init__(commandport,commandreadterm)
        self.greet()
        
    def greet(self):
        chrs = ''
        term = self.readterm
        while True:
            chunk = self.socket.recv(bufsize)
            for b in chunk:
                if b < 128:
                    chrs += chr(b)
                if chrs[-len(term):] == term:
                    return

    def read(self):
        msg = ''
        term = self.readterm
        while True:
            chunk = self.socket.recv(bufsize).decode('ascii')
            msg += chunk
            if msg[-len(term):] == term:
                return msg[:-len(term)]

    def send_command(self,command,*args):
        self.write(
            format_command(
                command,
                *args
            )
        )
        return self.read()

    def get_param(self,param,mode):
        rawvalue = self.send_command(
            'param-ref',
            format_param(param)
        )
        return parse_value(
            rawvalue,
            mode
        )
    
    def set_param(self,param,value,mode):
        return self.send_command(
            'param-set!',
            format_param(param),
            format_value(value,mode)
        )

    def get_motor_set_pos(self):
        return self.get_param(
            'laser1:nlo:opo:cavity:motor:position-set',
            FLOAT
        )

    def get_motor_act_pos(self):
        return self.get_param(
            'laser1:nlo:opo:cavity:motor:position-act',
            FLOAT
        )

    def set_motor_pos(self,pos):
        return self.set_param(
            'laser1:nlo:opo:cavity:motor:position-set',
            pos,
            INT
        )

    def get_etalon_pos(self):
        return self.get_param(
            'laser1:nlo:servo:etalon:value',
            INT
        )

    def set_etalon_pos(self,pos):
        return self.set_param(
            'laser1:nlo:servo:etalon:value',
            pos,
            INT
        )

    # sets diode current (in mA)
    def set_diode_current(self,current):
        return self.set_param(
            'laser1:dl:cc:current-set',
            current,
            FLOAT
        )

    def set_diode_temperature(self,temperature):
        return self.set_param(
            'laser1:dl:tc:temp-set',
            temperature,
            FLOAT
        )

    def get_diode_set_temperature(self):
        return self.get_param(
            'laser1:dl:tc:temp-set',
            FLOAT
        )

    def get_diode_act_temperature(self):
        return self.get_param(
            'laser1:dl:tc:temp-act',
            FLOAT
        )

segmentrestring = r'\(\S+ \S+ (.+)\)'
segmentre = re.compile(segmentrestring)
def parse_line(segment):
    return segmentre.fullmatch(segment).group(1)

class MonitoringClient(Client):
    def __init__(self,param,mode):
        super().__init__(monitoringport,monitoringreadterm)
        self.msg = ''
        self.subscribe(param)
        self.mode = mode

    def subscribe(self,param):
        self.write(
            format_command(
                'add',
                format_param(param)
            )                
        )

    def poll(self,timeout=None):
        self.socket.settimeout(timeout)
        term = self.readterm
        while True:
            if term in self.msg:
                segments = self.msg.split(term)
                line = segments.pop(0).strip()
                self.msg = term.join(segments)
                return parse_value(
                    parse_line(line),
                    self.mode
                )
                    
            try:
                chunk = self.socket.recv(bufsize).decode('ascii')
            except s.timeout:
                return None
            self.msg += chunk

    def wait(self,setpoint,epsilon=0,timeout=.05):
        while True:            
            value = self.poll(timeout)
            if value is None:
                continue
            if self.mode in (INT,FLOAT):                
                if abs(value-setpoint) <= epsilon:
                    return value
            else:
                if value == setpoint:
                    return value

def set_pos(pos,mode,setparam,actparam,epsilon):
    mc = MonitoringClient(actparam,mode)
    CommandClient().set_param(setparam,pos,mode)
    return mc.wait(pos,epsilon)

def get_motor_set_pos():
    return CommandClient().get_param(
        'laser1:nlo:opo:cavity:motor:position-set',
        FLOAT
    )

def get_motor_act_pos():
    return CommandClient().get_param(
        'laser1:nlo:opo:cavity:motor:position-act',
        FLOAT
    )

def set_motor_pos(pos,wait=True):
    if wait:
        return set_pos(
            pos,
            FLOAT,
            'laser1:nlo:opo:cavity:motor:position-set',
            'laser1:nlo:opo:cavity:motor:position-act',
            .001
        )
    else:
        return CommandClient().set_param(
            'laser1:nlo:opo:cavity:motor:position-set',
            pos,
            FLOAT
        )

def get_etalon_pos():
    return CommandClient().get_param(
        'laser1:nlo:servo:etalon:value',
        INT
    )

def set_etalon_pos(pos):
    return CommandClient().set_param(
        'laser1:nlo:servo:etalon:value',
        pos,
        INT
    )

# sets diode current (in mA)
def set_diode_current(current):
    return CommandClient().set_param(
        'laser1:dl:cc:current-set',
        current,
        FLOAT
    )

def set_diode_temperature(temperature):
    return CommandClient().set_param(
        'laser1:dl:tc:temp-set',
        temperature,
        FLOAT
    )

def get_diode_set_temperature():
    return CommandClient().get_param(
        'laser1:dl:tc:temp-set',
        FLOAT
    )

def get_diode_act_temperature():
    return CommandClient().get_param(
        'laser1:dl:tc:temp-act',
        FLOAT
    )

def get_diode_current():
    return CommandClient().get_param(
        'laser1:dl:cc:current-set',
        FLOAT
    )

def set_diode_current(current):
    return CommandClient().set_param(
        'laser1:dl:cc:current-set',
        current,
        FLOAT
    )
