from beckvisa import VisaSerialHandler
import pyvisa.constants, numpy as np

visaid = 'srsfg'
readterm = writeterm = '\r\n'
baudrate = 19200
databits = 8
parity = pyvisa.constants.Parity.none
stopbits = pyvisa.constants.StopBits.two

class SRSFGHandler(VisaSerialHandler):
    def __init__(self):
        super().__init__(visaid,readterm,writeterm,baudrate,databits,stopbits,parity)

    def configure(self,*args):
        super().configure(*args)        

NO_UNIT = ''

def query(handle,querystring):
    return handle.query(querystring)
def format_query(param):
    return '{}?'.format(param)
def get_parameter(handle,param,unit=NO_UNIT):    
    return float(query(handle,'{} {}'.format(format_query(param),unit)).replace(unit,NO_UNIT))

def set(handle,setstring):
    handle.write(setstring)

def format_set(param,value,unit=NO_UNIT):
    return '{} {:f}{}'.format(param, value, unit)
def set_parameter(handle,param,value,unit=NO_UNIT):
    return set(handle,format_set(param,value,unit))

def tune_parameter(handle,param,start,stop,step,unit=NO_UNIT):
    set(
        handle,
        ';'.join(
            format_set(
                param,value,unit
            ) 
            for value in 
            [*np.arange(start,stop,step if start < stop else -step),stop]
        )
    )

def get_id(handle):
    return query(handle,format_query('*idn')).strip()
RMS = 'VR'
VP = 'VP'
AMP = 'ampl'
def get_amplitude(handle,unit=RMS):
    return get_parameter(handle,AMP,unit)

def set_amplitude(handle,amplitude,unit):
    set_parameter(handle,AMP,amplitude,unit)

def tune_amplitude(handle,start,stop,step,unit=RMS):
    tune_parameter(handle,AMP,start,stop,step,unit)

FREQ = 'freq'

def get_frequency(handle):
    return get_parameter(handle,FREQ)

def set_frequency(handle,freq):
    return set_parameter(handle,FREQ,freq)

def get_status_byte(handle):
    return query(handle,format_query('*esr'))

def get_dds_byte(handle):
    return query(handle,format_query('stat'))

def clear_device(handle):
    return set(handle,'*cls')