from ctypes import *
from .daqmx import *

energy_output_channel = 'auger energy output'
current_input_channel = 'auger emission input'

def load_energy_output():
    handle = create_task()
    add_global_channel(handle,energy_output_channel)
    return handle

def set_energy_output(handle,energy):
    daqmx(        
        dll.DAQmxWriteAnalogScalarF64,
        handle,
        True,
        -1,
        c_double(energy),
        None
    )

def load_emission_input():
    handle = create_task()
    add_global_channel(handle,current_input_channel)
    return handle

def get_emission_input(handle):
    emission_current = c_double()
    daqmx(
        dll.DAQmxReadAnalogScalarF64,
        handle,
        -1,
        byref(emission_current),
        None
    )
    return emission_current.value

if __name__ == '__main__':

    energy_handle = load_energy_output()
    emission_handle = load_emission_input()

    set_energy_output(energy_handle,314)

    print(get_emission_input(emission_handle))

    for handle in (energy_handle, emission_handle):
        clear_task(handle)
