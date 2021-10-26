from beckutil import load_dll
import ctypes as c

dllname = 'TLPM_64.dll'

dll = load_dll(dllname)

devname = 'USB0::0x1313::0x807C::1909288::INSTR'

def open_pm():
    handle = c.c_uint()

    err = dll.TLPM_init(devname, True, False, c.byref(handle))
    if err:
        print('error opening device')
        raise(Exception(err))

    return handle

def close_pm(handle):
    err = dll.TLPM_close(instrHdl);
    if err:
        print('error closing device')
        raise(Exception(err))

def get_units(handle):
    unit = c.c_short()
    err = dll.TLPM_getPowerUnit(handle, c.byref(power_unit))
    if err:
        print('error getting power units')
        raise(Exception(err))
    return power_unit.value
    

def get_power(handle):
    power = c.c_double()
    err = dll.TLPM_measPower(handle, c.byref(power))
    if err:
        print('error measuring power')
        raise(Exception(err))
    return power.value

def get_error_message(handle,code):
    bufsize = 1024
    buf = c.create_string_buffer(bufsize)
    err = dll.TLPM_errorMessage(
        handle,
        code,
        buf
    )
    if err:
        print('error getting error message')
        raise Exception(err)
    return buf.value

pm = open_pm()
print(get_units(pm))
print(get_power(pm))
close_pm(pm)

