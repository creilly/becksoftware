from ctypes import *
from beckutil import load_dll

dll = windll.LoadLibrary('nicaiu.dll')
bufsize = 2 ** 10

class DAQmxError(Exception):
    def __init__(self,code):
        strbuf = create_string_buffer(bufsize)
        dll.DAQmxGetErrorString(code, strbuf, bufsize)
        super().__init__(
            'DAQmx error code {:d}:\t{}'.format(
                code,strbuf.value.decode('utf8')
            )
        )

class TaskHandler:
    def __init__(self,channels,global_task=False):
        if global_task:
            self.task = load_task(channels) # channels here should be global task name
        else:
            self.task = task = create_task()
            for channel in channels:
                add_global_channel(task,channel)

    def __enter__(self):
        return self.task

    def __exit__(self,*args):
        clear_task(self.task)

class LineHandler:
    def __init__(self,channel):
        self.line = load_line(channel)

    def __enter__(self):
        return self.line

    def __exit__(self,*args):
        close_line(self.line)

def _pystr_to_cstr(pystr):
    return pystr.encode()

def daqmx(func,*args):
    result = func(*args)
    if result: raise DAQmxError(result)

def create_task():
    handle = c_voidp()
    daqmx(
        dll.DAQmxCreateTask,
        None,
        byref(handle)
    )
    return handle

def clear_task(handle):
    daqmx(
        dll.DAQmxClearTask,
        handle
    )
    
def add_global_channel(handle,channel):
    daqmx(
        dll.DAQmxAddGlobalChansToTask,
        handle, 
        channel.encode()
    )

def get_phys_chan_name(handle):
    name = create_string_buffer(bufsize)
    daqmx(
        dll.DAQmxGetPhysicalChanName,
        handle,
        None,
        name,
        bufsize
    )
    return name.value

def start_task(handle):
    daqmx(
        dll.DAQmxStartTask,
        handle,
    )

def task_wait(handle):
    daqmx(
        dll.DAQmxWaitUntilTaskDone,
        handle,
        c_double(-1)
    )

def is_task_done(handle):
    task_done = c_uint32()
    daqmx(
        dll.DAQmxIsTaskDone,
        handle,
        byref(task_done)
    )
    return bool(task_done.value)

def stop_task(handle):
    daqmx(
        dll.DAQmxStopTask,
        handle,
    )

def get_exponent(taskhandle):
    strbuf = create_string_buffer(bufsize)
    daqmx(
        dll.DAQmxGetPhysicalChanName,
        taskhandle,
        None,
        strbuf,
        bufsize
    )
    return int(
        strbuf.value.decode('utf8').split(', ')[0].split('/')[-1].split('line')[-1]
    )

def load_line(channel):
    taskhandle = create_task()
    add_global_channel(taskhandle,channel)
    exp = get_exponent(taskhandle)
    return (taskhandle,exp)

def close_line(line):
    taskhandle, exp = line
    clear_task(taskhandle)

def write_line(line,state):
    handle, exp = line
    daqmx(
        dll.DAQmxWriteDigitalScalarU32,
        handle,
        True,
        -1,
        int(state) * 2 ** exp,
        None
    )

def set_samples(handle,samples):
    daqmx(
        dll.DAQmxSetSampQuantSampPerChan,
        handle,
        c_uint64(samples)
    )

IMPLICIT_TIMING = 10451
def set_samp_timing_type(handle,timing_type):
    daqmx(
        dll.DAQmxSetSampTimingType,
        handle,
        timing_type
    )

def get_samp_clk_src(handle):
    source = create_string_buffer(bufsize)
    daqmx(
        dll.DAQmxGetSampClkSrc,
        handle,
        source,
        bufsize
    )
    return source

def get_samp_clk_rate(handle):
    rate = c_double()
    daqmx(
        dll.DAQmxGetSampClkRate,
        handle, 
        byref(rate)
    )
    return rate.value

def set_samp_clk_rate(handle,rate):    
    daqmx(
        dll.DAQmxSetSampClkRate,
        handle, 
        c_double(rate)
    )    

FINITE_SAMPS = 10178
CONT_SAMPS = 10123
RISING = 10280
FALLING = 10171
ONBOARD_CLK = None
def cfg_samp_clk_timing(handle,rate,mode,samps,src=ONBOARD_CLK):
    daqmx(
        dll.DAQmxCfgSampClkTiming,
        handle,
        src if src is None else src.encode(),
        c_double(rate),
        RISING,
        mode,
        samps
    )

def cfg_implicit_timing(handle,mode,buffersize):
    daqmx(
        dll.DAQmxCfgImplicitTiming,
        handle,
        mode,
        buffersize        
    )

def cfg_trigger(handle,src):
    daqmx(
        dll.DAQmxCfgDigEdgeStartTrig,
        handle,
        src,
        RISING
    )

def get_co_term(handle):
    term = create_string_buffer(bufsize)
    daqmx(
        dll.DAQmxGetCOPulseTerm,
        handle,
        None,
        term,
        bufsize
    )
    return term.value

def set_co_term(handle,term):
    daqmx(
        dll.DAQmxSetCOPulseTerm,
        handle,
        None,
        term
    )

WAIT_INFINITELY = c_double(-1.0)
def write_sample(handle,value):
    stt = get_samp_timing_type(handle)
    set_samp_timing_type(handle,ON_DEMAND)
    daqmx(        
        dll.DAQmxWriteAnalogScalarF64,
        handle,
        True,
        WAIT_INFINITELY,
        c_double(value),
        None
    )
    set_samp_timing_type(handle,stt)

GROUP_BY_CHANNEL = 0
def write_to_buff(handle,*datas):
    data = []
    for d in datas:
        datasize = len(d)
        data.extend(d)
    samps_written = c_int32()
    daqmx(
        dll.DAQmxWriteAnalogF64,
        handle,
        datasize,
        False,
        WAIT_INFINITELY,
        GROUP_BY_CHANNEL,
        (c_double*(datasize*len(datas)))(*data),
        byref(samps_written),
        None
    )

def get_samps_acquired(handle):
    samps = c_uint64()
    daqmx(
        dll.DAQmxGetReadTotalSampPerChanAcquired,
        handle,
        byref(samps)
    )
    return samps.value

def get_samps_generated(handle):
    samps = c_uint64()
    daqmx(
        dll.DAQmxGetWriteTotalSampPerChanGenerated,
        handle,
        byref(samps)
    )
    return samps.value

def get_num_chans(handle):
    nchans = c_uint32()
    daqmx(
        dll.DAQmxGetTaskNumChans,
        handle,
        byref(nchans)
    )
    return nchans.value

def read_analog_f64_scalar(handle):
    scalar = c_double()
    daqmx(
        dll.DAQmxReadAnalogScalarF64,
        handle,
        WAIT_INFINITELY,
        byref(scalar),
        None
    )
    return scalar.value

def read_analog_f64(handle,samps,arrsize,nchans=None):
    if nchans is None:
        nchans = get_num_chans(handle)
    data = (c_double*arrsize)()
    samps_read = c_int32()
    daqmx(
        dll.DAQmxReadAnalogF64,
        handle,
        samps,
        c_double(1.0), # WAIT_INFINITELY,
        GROUP_BY_CHANNEL,
        data,
        arrsize,
        byref(samps_read),
        None
    )
    samps_read = samps_read.value
    return [
        data[n*samps_read:(n+1)*samps_read] for n in range(nchans)
    ]    

def read_all(handle,arrsize,nchans=None):
    return read_analog_f64(handle,-1,arrsize,nchans)
    
def read_buff(handle,samps,nchans=None):
    if nchans is None:
        nchans = get_num_chans(handle)
    arrsize = nchans*samps
    return read_analog_f64(handle,samps,arrsize,nchans)

def get_samp_clk_term(handle):
    term_name = create_string_buffer(bufsize)
    daqmx(
        dll.DAQmxGetSampClkTerm,
        handle,
        term_name,
        bufsize
    )
    return term_name.value.decode('utf8')

def load_task(name):
    handle = c_voidp()
    daqmx(
        dll.DAQmxLoadTask,
        name.encode(),
        byref(handle)
    )
    return handle

def get_sys_tasks():
    tasklist = create_string_buffer(bufsize)
    daqmx(
        dll.DAQmxGetSysTasks,
        tasklist,
        bufsize
    )
    return tasklist.value.decode('utf8').split(', ')

SAMP_CLK = 10388
ON_DEMAND = 10390
def get_samp_timing_type(handle):    
    stt = c_int32()
    daqmx(
        dll.DAQmxGetSampTimingType,
        handle,
        byref(stt)
    )
    return stt.value

def set_samp_timing_type(handle,stt):
    daqmx(
        dll.DAQmxSetSampTimingType,
        handle,
        stt
    )

ALLOW_REGEN = 10097
DO_NOT_ALLOW_REGEN = 10158
def set_regeneration_mode(handle,enabled):
    daqmx(
        dll.DAQmxSetWriteRegenMode,
        handle,
        {
            True:ALLOW_REGEN,
            False:DO_NOT_ALLOW_REGEN
        }[enabled]
    )

# DAQmx_Val_FirstSample 10424 Write samples relative to the first sample. 
# DAQmx_Val_CurrWritePos 10430 Write samples relative to the current position in the buffer.

def set_ci_count_edges_term(handle,term):
    daqmx(
        dll.DAQmxSetCICountEdgesTerm,
        handle,
        None,
        term.encode()
    )

def get_ci_count_edges_term(handle):
    term = create_string_buffer(bufsize)
    daqmx(
        dll.DAQmxGetCICountEdgesTerm,
        handle,
        None,
        term,
        bufsize
    )
    return term.value.decode('utf8')

def get_timebase_divisor(handle):
    divisor = c_uint32()
    daqmx(
        dll.DAQmxGetSampClkTimebaseDiv,
        handle,
        byref(divisor)
    )
    return divisor.value

def get_timebase_rate(handle):
    rate = c_double()
    daqmx(
        dll.DAQmxGetSampClkTimebaseRate,
        handle,
        byref(rate)
    )
    return rate.value

def set_timebase_src(handle,src):
    daqmx(
        dll.DAQmxSetSampClkTimebaseSrc,
        handle,
        src.encode()
    )

def cfg_arm_start_trig(handle,src,edge):
    set_arm_start_trig_type(handle,DIG_EDGE)
    set_dig_edge_arm_start_trig_src(handle,src)
    set_dig_edge_arm_start_trig_edge(handle,edge)

DIG_EDGE = 10150
def set_arm_start_trig_type(handle,type):
    daqmx(
        dll.DAQmxSetArmStartTrigType,
        handle,
        type
    )

def set_dig_edge_arm_start_trig_src(handle,src):
    daqmx(
        dll.DAQmxSetDigEdgeArmStartTrigSrc,
        handle,
        src.encode()
    )

def set_dig_edge_arm_start_trig_edge(handle,edge):
    daqmx(
        dll.DAQmxSetDigEdgeArmStartTrigEdge,
        handle,
        edge
    )

def read_counter_u32_single_channel_non_blocking(handle,samps):
    data = (c_uint32*samps)()
    samps_read = c_int32()
    daqmx(
        dll.DAQmxReadCounterU32,
        handle,
        -1,
        WAIT_INFINITELY,
        data,
        samps,
        byref(samps_read),
        None
    )
    return data[:samps_read.value]

def write_ticks_scalar(handle,highticks,lowticks,autostart=False,timeout=None):
    timeout = WAIT_INFINITELY if timeout is None else c_double(timeout)
    daqmx(
        dll.DAQmxWriteCtrTicksScalar,
        handle,
        {
            False:0,True:1
        }[autostart],
        timeout,
        highticks,
        lowticks,
        None
    )

def write_ticks(handle,*tickpair_arrs):
    tick_stacks = [[],[]]    
    for tickpair_arr in tickpair_arrs:
        for tick_stack, tick_substack in zip(
            tick_stacks,
            zip(*tickpair_arr)
        ):        
            tick_stack.extend(tick_substack)
    n_samps_per_chan = len(tick_stack) // len(tickpair_arrs)
    high_ticks, low_ticks = [
        (c_uint32*len(tick_stack))(*tick_stack)
        for tick_stack in tick_stacks
    ]
    samps_written = c_int32()
    daqmx(
        dll.DAQmxWriteCtrTicks,
        handle,
        n_samps_per_chan,
        False,
        WAIT_INFINITELY,
        GROUP_BY_CHANNEL,
        high_ticks, low_ticks,
        byref(samps_written),
        None
    )

def set_ticks(handle,highticks,lowticks):
    for ticks, function in (
            (highticks,dll.DAQmxSetCOPulseHighTicks),
            (lowticks,dll.DAQmxSetCOPulseLowTicks)
    ):
        daqmx(
            function,
            handle,
            '',
            ticks
        )

def get_co_type(handle):
    co_type = c_uint32()
    daqmx(
        dll.DAQmxGetCOOutputType,
        handle,
        None,
        byref(co_type)
    )
    return co_type.value

IDLE_HIGH = 10192
IDLE_LOW = 10214
def create_co_ticks_channel(handle,physical_channel,highticks,lowticks,source_terminal=None):
    daqmx(
        dll.DAQmxCreateCOPulseChanTicks,
        handle,
        physical_channel.encode(),
        None,
        source_terminal,
        IDLE_HIGH,
        0, # initial delay
        lowticks,
        highticks
    )

def get_physical_channel(handle):
    pc = create_string_buffer(bufsize)
    daqmx(
        dll.DAQmxGetPhysicalChanName,
        handle,
        None,
        pc,
        bufsize
    )
    return pc.value.decode('utf8')

def get_samps_per_channel(handle):
    samps_per_channel = c_uint64()
    daqmx(
        dll.DAQmxGetSampQuantSampPerChan,
        handle, 
        byref(samps_per_channel)
    )
    return samps_per_channel.value

def read_counter_f64(handle, samps):
    data = (c_double*samps)()
    samples_read = c_int32()
    daqmx(
        dll.DAQmxReadCounterF64,
        handle, -1, 0, data, samps, byref(samples_read), None
    )
    return data, samples_read.value

def read_counter_f64_scalar(handle):
    datum = c_double()
    daqmx(
        dll.DAQmxReadCounterScalarF64,
        handle, c_double(1.0), byref(datum), None
    )
    return datum.value

if __name__ == '__main__':
    exit(0)
