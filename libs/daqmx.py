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
    def __init__(self,channels):
        self.task = task = create_task()
        for channel in channels:
            add_global_channel(task,channel)

    def __enter__(self):
        return self.task

    def __exit__(self,*args):
        clear_task(self.task)

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
        taskhandle,
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

FINITE_SAMPS = 10178
CONT_SAMPS = 10123
RISING = 10280
ONBOARD_CLK = None
def cfg_samp_clk_timing(handle,rate,mode,samps):
    daqmx(
        dll.DAQmxCfgSampClkTiming,
        handle,
        ONBOARD_CLK,
        c_double(rate),
        RISING,
        mode,
        samps
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
    daqmx(        
        dll.DAQmxWriteAnalogScalarF64,
        handle,
        True,
        WAIT_INFINITELY,
        c_double(value),
        None
    )

GROUP_BY_CHANNEL = 0
def write_to_buff(handle,data):
    datasize = len(data)
    samps_written = c_int32()
    daqmx(
        dll.DAQmxWriteAnalogF64,
        handle,
        datasize,
        False,
        WAIT_INFINITELY,
        GROUP_BY_CHANNEL,
        (c_double*datasize)(*data),
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

def read_buff(handle,samps):
    nchans = get_num_chans(handle)
    arrsize = nchans*samps
    data = (c_double*arrsize)()
    samps_read = c_int32()
    daqmx(
        dll.DAQmxReadAnalogF64,
        handle,
        samps,
        WAIT_INFINITELY,
        GROUP_BY_CHANNEL,
        data,
        arrsize,
        byref(samps_read),
        None
    )
    return [
        data[n*samps:(n+1)*samps] for n in range(nchans)
    ]

if __name__ == '__main__':
    cotask = create_task()
    add_global_channel(cotask,'topo scan trigger')
    print(get_samp_clk_src(cotask).value)
    print(get_phys_chan_name(cotask))
    print(get_co_term(cotask))
