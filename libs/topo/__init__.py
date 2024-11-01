import socket as s
import re
from base64 import b64decode
import struct
import math
import time
import select

IP = '192.168.2.3'
commandport = 1998
monitoringport = 1999

writeterm = b'\n'
commandreadterm = b'\n' + b'> '
monitoringreadterm = b'\n'

bufsize = 256

class Client:
    def __init__(self,port,readterm):
        socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        socket.setsockopt(s.IPPROTO_TCP, s.TCP_NODELAY,1)
        socket.connect((IP,port))
        self.socket = socket
        self.readterm = readterm
        
    def write(self,msg):
        msg += writeterm        
        self.socket.sendall(msg)        

    def query(self,command):
        self.write(command)
        return self.read()

    def close(self):
        self.socket.close()

STR, INT, FLOAT, BOOL, BIN = 0, 1, 2, 3, 4
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

intsize = 4
def parse_bin_int(data):
    return [
        int.from_bytes(
            data[4*i:4*(i+1)],
            'little',
            signed = True
        )
        for i in range(len(data)//4)
    ]

def parse_bin_float(data):
    return struct.unpack('{:d}f'.format(len(data)//4),data)

def parse_binary(b64bs):
    blocks = []    
    
    bs = b64decode(b64bs)
    n = 0
    N = len(bs)
    
    while True:
        blockname = chr(bs[n])
        n += 1
        countstr = ''
        while True:
            b = bs[n]
            n += 1
            if b:
                countstr += chr(b)                
                continue            
            break
        count = int(countstr)
        blocks.append((blockname,bs[n:n+count]))
        n += count
        if n == N:
            return blocks

def format_instruction(command,*parameters):
    return '({})'.format(
        ' '.join([command] + list(parameters))
    ).encode()

def format_param(param):
    return '\'{}'.format(param)

class SetParamError(Exception):
    pass

def do_nothing(x): return x

class InstructionClient(Client):
    def __init__(self):
        super().__init__(commandport,commandreadterm)
        self.greet()
        
    def greet(self):
        return self.read()
        # chrs = b''
        # term = self.readterm
        # while True:
        #     chunk = self.socket.recv(bufsize)
        #     for i in range(len(chunk)):
        #         chrs += chunk[i:i+1]
        #         if chrs[-len(term):] == term:
        #             return
                
    def read(self):
        msg = b''
        term = self.readterm
        while True:
            chunk = self.socket.recv(bufsize)
            msg += chunk
            if msg[-len(term):] == term:
                return msg[:-len(term)]

    def write_instruction(self,instruction,*args):
        self.write(
            format_instruction(
                instruction,
                *args
            )
        )
        
    def send_instruction(self,instruction,*args):
        self.write_instruction(instruction,*args)
        return self.read()

    def send_command(self,command,*args):
        return self.send_instruction(
            'exec',
            format_param(command),
            *[
                format_value(
                    *arg
                ) for arg in args
            ]
        )

    def get_param(self,param,mode):
        rawvalue = self.send_instruction(
            'param-ref',
            format_param(param)
        ).decode('ascii')
        return parse_value(
            rawvalue,
            mode
        )
    
    def set_param(self,param,value,mode):
        response = self.send_instruction(
            'param-set!',
            format_param(param),
            format_value(value,mode)
        )
        response = response.decode('ascii')
        if not response.isdigit():
            raise SetParamError(response)
        return int(response)

    # MOTOR

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

    # ETALON

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

    # DIODE CURRENT

    def get_diode_current(self):
        return self.get_param(
            'laser1:dl:cc:current-set',
            FLOAT
        )

    def set_diode_current(self,current):
        return self.set_param(
            'laser1:dl:cc:current-set',
            current,
            FLOAT
        )

    def get_analog_current_scaling_factor(self):
        return self.get_param(
            'laser1:dl:cc:external-input:factor',
            FLOAT
        )

    def set_analog_current_scaling_factor(self,factor):
        return self.set_param(
            'laser1:dl:cc:external-input:factor',
            factor,
            FLOAT
        )

    def get_analog_current_enabled(self):
        return self.get_param(
            'laser1:dl:cc:external-input:enabled',
            BOOL
        )

    def set_analog_current_enabled(self,enabled):
        return self.set_param(
            'laser1:dl:cc:external-input:enabled',
            enabled,
            BOOL
        )

    # DIODE TEMPERATURE

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

    def get_analog_temperature_scaling_factor(self):
        return self.get_param(
            'laser1:dl:tc:external-input:factor',
            FLOAT
        )

    def set_analog_temperature_scaling_factor(self,factor):
        return self.set_param(
            'laser1:dl:tc:external-input:factor',
            factor,
            FLOAT
        )

    def get_analog_temperature_enabled(self):
        return self.get_param(
            'laser1:dl:tc:external-input:enabled',
            BOOL
        )

    def set_analog_temperature_enabled(self,enabled):
        return self.set_param(
            'laser1:dl:tc:external-input:enabled',
            enabled,
            BOOL
        )

    def get_diode_temperature_ready(self):
        return self.get_param(
            'laser1:dl:tc:ready',
            BOOL
        )

    # OPO PIEZO

    def set_piezo(self,voltage):
        return self.set_param(
            'laser1:nlo:opo:cavity:slow-pzt-voltage-set',
            voltage,
            FLOAT
        )

    def get_piezo(self):
        return self.get_param(
            'laser1:nlo:opo:cavity:slow-pzt-voltage-set',
            FLOAT
        )

    # WIDE SCAN

    def start_wide_scan(self):
        return self.send_command(
            'laser1:wide-scan:start'
        )

    def stop_wide_scan(self):
        return self.send_command(
            'laser1:wide-scan:stop'
        )

    def get_wide_scan_data(self,start,count):
        result = parse_binary(
            self.send_command(
                'laser1:recorder:data:get-data',
                (start,INT),(count,INT)
            )
        )
        (i,idataraw),(x,xdataraw), *ytups = result        
        idata = parse_bin_int(idataraw)
        xdata = parse_bin_float(xdataraw)
        ydatas = []
        for y, ydataraw in ytups:
            ydatas.append(parse_bin_float(ydataraw))        
        return idata,xdata,*ydatas

    def get_wide_scan_length(self):
        return self.get_param(
            'laser1:recorder:data:recorded-sample-count',
            INT
        )

    def get_wide_scan_begin(self):
        return self.get_param(
            'laser1:wide-scan:scan-begin',
            FLOAT
        )

    def set_wide_scan_begin(self,voltage):
        return self.set_param(
            'laser1:wide-scan:scan-begin',
            voltage,
            FLOAT
        )

    def get_wide_scan_end(self):
        return self.get_param(
            'laser1:wide-scan:scan-end',
            FLOAT
        )

    def set_wide_scan_end(self,voltage):
        return self.set_param(
            'laser1:wide-scan:scan-end',
            voltage,
            FLOAT
        )

    def set_wide_scan_step(self,voltage):
        return self.set_param(
            'laser1:wide-scan:recorder-stepsize-set',
            voltage,
            FLOAT
        )
    
    def set_wide_scan_input(self,virtual_channel,physical_channel):
        return self.set_param(
            'laser1:recorder:inputs:channel{:d}:signal'.format(virtual_channel),
            physical_channel,
            INT
        )
    
    def get_wide_scan_input(self,virtual_channel):
        return self.get_param(
            'laser1:recorder:inputs:channel{:d}:signal'.format(virtual_channel),
            INT
        )
    
    def get_wide_scan_output(self):
        return self.get_param(
            'laser1:wide-scan:output-channel',
            INT
        )
    
    def set_wide_scan_output(self,channel):
        return self.set_param(
            'laser1:wide-scan:output-channel',
            channel,
            INT
        )

    # in milliseconds
    def get_wide_scan_sampling_interval(self):
        return self.get_param(
            'laser1:wide-scan:recorder-sampling-interval',
            FLOAT
        )
    
    # volts / second
    def get_wide_scan_speed(self):
        return self.get_param(
            'laser1:wide-scan:speed',
            FLOAT
        )
    
    def set_wide_scan_speed(self,speed):
        return self.set_param(
            'laser1:wide-scan:speed',
            speed,
            FLOAT
        )

    # SIGNAL POWER

    def get_signal_power(self):
        return self.get_param(
            'laser1:nlo:pd:sig:power',
            FLOAT
        )

    # LOCK

    def set_locking(self,locking):
        return self.send_command(
            {
                True:'laser1:dl:lock:close',
                False:'laser1:dl:lock:open'
            }[locking]
        )

    def set_modulating(self,modulating):
        return self.set_param(
            'laser1:dl:lock:lockin:modulation-enabled',
            modulating,
            BOOL
        )

    # IO
    # channel should be module variable A (integer value 0)
    # or B (integer value 1) for outputs A or B, respectively
    def set_output(self,channel,voltage):
        return self.set_param(
            'io:out-{}:voltage-set'.format(
                {
                    A:'a',
                    B:'b'
                }[channel]
            ),
            voltage,
            FLOAT
        )

    def get_output(self,channel):
        return self.get_param(
            'io:out-{}:voltage-set'.format(
                {
                    A:'a',
                    B:'b'
                }[channel]
            ),
            FLOAT
        )

    def get_input(self,channel):
        return self.get_param(
            'io:{}:value-act'.format(
                {
                    FINE1:'fine-1',
                    FINE2:'fine-2',
                    FAST3:'fast-3',
                    FAST4:'fast-4',
                }[channel]
            ),
            FLOAT
        )   
    
    # buzzer

    def play_welcome(self):
        return self.send_command('buzzer:play-welcome')
    
    def play_melody(self, melody):
        return self.send_command('buzzer:play',(melody,STR))

class ScopeClient:
    def __init__(self):
        self.mc = MonitoringClient('laser1:scope:data',STR)

    def get_trace(self,timeout):
        response = self.mc.poll(timeout)
        if response is None:
            return None
        *ys, x = [
            parse_bin_float(data) for label, data in parse_binary(response)
        ]
        return x, *ys

class AsyncResponse:
    def __init__(self,aic,cb):
        self.aic = aic
        self.cb = cb
        self.fulfilled = False

    def read(self):
        if self.fulfilled:
            return (True,self.response)
        self.aic.read_async()
        if self.fulfilled:
            return (True,self.response)
        return (False,None)

    def read_blocking(self):
        while True:
            f, r = self.read()
            if f: return r                

    def fulfill(self,rawvalue):
        self.response = self.cb(rawvalue)
        self.fulfilled = True

class AsyncInstructionClient(InstructionClient):
    def __init__(self):
        super().__init__()
        self.socket.setblocking(False)
        self.head = b''
        self.queue = []

    def read_async(self):
        msg = self.head
        term = self.readterm
        while True:
            try:
                chunk = self.socket.recv(bufsize)
            except BlockingIOError:
                self.head = msg
                return
            msg += chunk
            while term in msg:
                head, tail = msg.split(term,1)
                self.queue.pop(0).fulfill(head)
                msg = tail

    def send_instruction(self,cb,instruction,*args):
        # caution! not thread safe!
        self.socket.setblocking(True)
        self.write_instruction(instruction,*args)
        self.socket.setblocking(False)
        asyncresponse = AsyncResponse(self,cb)
        self.queue.append(asyncresponse)
        return asyncresponse

    @staticmethod
    def get_gp_cb(mode):
        def cb(rawvalue):            
            return parse_value(rawvalue.decode('ascii'),mode)
        return cb

    @staticmethod
    def sp_cb(rawresponse):
        response = rawresponse.decode('ascii')
        if not response.isdigit():
            raise SetParamError(response)
        return int(response)

    def send_command(self,command,*args,cb=do_nothing):
        return self.send_instruction(
            cb,
            'exec',
            format_param(command),
            *[
                format_value(
                    *arg
                ) for arg in args
            ]
        )

    def get_param(self,param,mode):
        return self.send_instruction(
            self.get_gp_cb(mode),
            'param-ref',
            format_param(param)
        )
    
    def set_param(self,param,value,mode):
        return self.send_instruction(
            self.sp_cb,
            'param-set!',
            format_param(param),
            format_value(value,mode)
        )

    @staticmethod
    def gws_cb(rawdata):
        return [
            parser(zdataraw) for parser, (z,zdataraw) in zip(
                zip(
                    parse_binary(rawdata),
                    [parse_bin_int] + [parse_bin_float]*3
                )
            )
        ]
        (i,idataraw),(x,xdataraw),(y,ydataraw),(Y,Ydataraw) = parse_binary(rawdata)

    def get_wide_scan_data(self,start,count):
        return self.send_command(
            'laser1:recorder:data:get-data',
            (start,INT),(count,INT),
            cb = self.gws_cb
        )

A, B = 0, 1
WS_A, WS_B, WS_DC, WS_DT, WS_PZ = 20, 21, 51, 56, 50
FINE1, FINE2, FAST3, FAST4, NOINPUT = 0, 1, 2, 3, -3
INPUT1, INPUT2 = 1, 2
segmentrestring = r'\(\S+ \S+ (.+)\)'
segmentre = re.compile(segmentrestring)
def parse_line(segment):
    return segmentre.fullmatch(segment).group(1)

class MonitoringClient(Client):
    def __init__(self,param,mode):
        super().__init__(monitoringport,monitoringreadterm)
        self.msg = b''
        self.subscribe(param)
        self.mode = mode

    def subscribe(self,param):
        self.write(
            format_instruction(
                'add',
                format_param(param)
            )                
        )

    def poll(self,timeout=None):
        blocking = timeout != 0
        if blocking:
            self.socket.settimeout(timeout)
        else:
            self.socket.setblocking(False)
        term = self.readterm
        while True:
            if term in self.msg:
                segments = self.msg.split(term)
                line = segments.pop(0)
                self.msg = term.join(segments)
                return parse_value(
                    parse_line(line.decode('ascii').strip()),
                    self.mode
                )
            if blocking:
                try:
                    chunk = self.socket.recv(bufsize)
                except s.timeout:
                    return None
            else:
                rs, *_ = select.select((self.socket,),(),(),0)
                if rs:
                    chunk = self.socket.recv(bufsize)
                else:
                    return None
            self.msg += chunk

    def wait(self,setpoint,epsilon=0,looptimeout=.05,timeout=math.inf):
        starttime = time.time()
        while True:
            value = self.poll(looptimeout)
            if time.time() - starttime > timeout:
                return None
            if value is None:
                continue
            if self.compare(setpoint,value,epsilon):
                return value
            
    def compare(self,setpoint,value,epsilon):
        if self.mode in (INT,FLOAT):                
            return abs(value-setpoint) <= epsilon                
        else:
            return value == setpoint
                
    def wait_async(self,setpoint,epsilon=0):
        while True:
            value = self.poll(0)
            if value is not None and self.compare(setpoint,value,epsilon):
                return value
            yield
                
SCAN_DISABLED = 0
def get_wide_scan(ic : InstructionClient):
    ic.start_wide_scan()
    mc = MonitoringClient('laser1:wide-scan:state',INT)
    mc.wait(SCAN_DISABLED)
    return finish_scan(ic)

def get_wide_scan_async(ic : InstructionClient):
    ic.start_wide_scan()
    mc = MonitoringClient('laser1:wide-scan:state',INT)
    yield from mc.wait_async(SCAN_DISABLED)
    return finish_scan(ic)

def finish_scan(ic : InstructionClient):
    scanlen = ic.get_wide_scan_length()
    scanindex = 0
    xdata = []
    ydatas = {}
    while scanindex < scanlen:
        (istart,icount),xchunk,*ychunks = ic.get_wide_scan_data(scanindex,scanlen-scanindex)
        xdata += xchunk
        for index, ychunk in enumerate(ychunks):
            ydatas.setdefault(index,[]).extend(ychunk)            
        scanindex = istart + icount
    return xdata, *(ydatas[index] for index in sorted(ydatas))

def set_pos(pos,mode,setparam,actparam,epsilon):
    mc = MonitoringClient(actparam,mode)
    InstructionClient().set_param(setparam,pos,mode)
    return mc.wait(pos,epsilon)

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
        return InstructionClient().set_param(
            'laser1:nlo:opo:cavity:motor:position-set',
            pos,
            FLOAT
        )

# vvvvvvvvv deprecated. use the InstructionClient methods

def get_motor_set_pos():
    return InstructionClient().get_param(
        'laser1:nlo:opo:cavity:motor:position-set',
        FLOAT
    )

def get_motor_act_pos():
    return InstructionClient().get_param(
        'laser1:nlo:opo:cavity:motor:position-act',
        FLOAT
    )

def get_etalon_pos():
    return InstructionClient().get_param(
        'laser1:nlo:servo:etalon:value',
        INT
    )

def set_etalon_pos(pos):
    return InstructionClient().set_param(
        'laser1:nlo:servo:etalon:value',
        pos,
        INT
    )

# sets diode current (in mA)
def set_diode_current(current):
    return InstructionClient().set_param(
        'laser1:dl:cc:current-set',
        current,
        FLOAT
    )

def set_diode_temperature(temperature):
    return InstructionClient().set_param(
        'laser1:dl:tc:temp-set',
        temperature,
        FLOAT
    )

def get_diode_set_temperature():
    return InstructionClient().get_param(
        'laser1:dl:tc:temp-set',
        FLOAT
    )

def get_diode_act_temperature():
    return InstructionClient().get_param(
        'laser1:dl:tc:temp-act',
        FLOAT
    )

def get_diode_current():
    return InstructionClient().get_param(
        'laser1:dl:cc:current-set',
        FLOAT
    )

def set_diode_current(current):
    return InstructionClient().set_param(
        'laser1:dl:cc:current-set',
        current,
        FLOAT
    )

def get_analog_temperature_scaling_factor():
    return InstructionClient().get_param(
        'laser1:dl:tc:external-input:factor',
        FLOAT
    )

def set_analog_temperature_scaling_factor(factor):
    return InstructionClient().set_param(
        'laser1:dl:tc:external-input:factor',
        factor,
        FLOAT
    )

def get_analog_temperature_enabled():
    return InstructionClient().get_param(
        'laser1:dl:tc:external-input:enabled',
        BOOL
    )

def set_analog_temperature_enabled(enabled):
    return InstructionClient().set_param(
        'laser1:dl:tc:external-input:enabled',
        enabled,
        BOOL
    )

def get_diode_temperature_ready():
    return InstructionClient().get_param(
        'laser1:dl:tc:ready',
        BOOL
    )

def get_analog_current_scaling_factor():
    return InstructionClient().get_param(
        'laser1:dl:cc:external-input:factor',
        FLOAT
    )

def set_analog_current_scaling_factor(factor):
    return InstructionClient().set_param(
        'laser1:dl:cc:external-input:factor',
        factor,
        FLOAT
    )

def get_analog_current_enabled():
    return InstructionClient().get_param(
        'laser1:dl:cc:external-input:enabled',
        BOOL
    )

def set_analog_current_enabled(enabled):
    return InstructionClient().set_param(
        'laser1:dl:cc:external-input:enabled',
        enabled,
        BOOL
    )

def set_piezo(voltage):
    return InstructionClient().set_param(
        'laser1:nlo:opo:cavity:slow-pzt-voltage-set',
        voltage,
        FLOAT
    )

def get_piezo():
    return InstructionClient().get_param(
        'laser1:nlo:opo:cavity:slow-pzt-voltage-set',
        FLOAT
    )

def get_signal_power():
    return InstructionClient().get_param(
        'laser1:nlo:pd:sig:power',
        FLOAT
    )