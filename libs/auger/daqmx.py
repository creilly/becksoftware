from ctypes import *

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

def daqmx(func,*args):
    result = func(*args)
    if result: raise DAQmxError(result)

def create_task():
    handle = c_int32()
    daqmx(
        dll.DAQmxCreateTask,
        None,
        byref(handle)
    )
    return handle.value

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
