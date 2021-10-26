import pyvisa
from pyvisa.constants import AccessModes

LOCKIN_VISA_NAME = 'bilt-lockin'

class LockinHandler:
    def __init__(self,name=LOCKIN_VISA_NAME):
        self.lockin = load_lockin(name)

    def __enter__(self):
        return self.lockin

    def __exit__(self,*args):
        close_lockin(self.lockin)

def load_lockin(name=LOCKIN_VISA_NAME):
    lockin = pyvisa.ResourceManager().open_resource(name)
    lockin.lock_excl(timeout=5000.0)
    return lockin

def load_lockin_preset(lockin,preset_number):
    lockin.write('RSET {:d}'.format(preset_number))

def read_lockin(lockin):
    return float(lockin.query('OUTP ? 1').strip())

def get_xy(lockin):
    return list(map(float,lockin.query('SNAP?1,2').split(',')))

def get_xya(lockin):
    return list(map(float,lockin.query('SNAP?1,2,5').split(',')))

def close_lockin(lockin):
    lockin.close()

sample_rates = (
    62.5e-3,
    125e-3, 250e-3, 500e-3,
    1.0, 2.0, 4.0, 8.0,
    16.0, 32.0, 64.0,
    128.0, 256.0, 512.0,
    -1.0
)

time_constants = (
    10e-6, 30e-6, 100e-6, 300e-6, 
    1e-3, 3e-3, 10e-3, 30e-3, 100e-3, 300e-3, 
    1e-0, 3e-0, 10e-0, 30e-0, 100e-0, 300e-0, 
    1e+3, 3e+3, 10e+3, 30e+3
)

def set_time_constant(lockin, time_constant):
    index, time_constant = get_closest_value(time_constants, time_constant)
    lockin.write('OFLT {:d}'.format(index))
    return time_constant

def get_time_constant(lockin):
    return time_constants[int(lockin.query('OFLT?'))]

def get_time_constants():
    return time_constants

def get_closest_value(arr,value):   
    return min(
        enumerate(arr),
        key=lambda x: abs(x[1]-value)
    )

def set_sample_rate(lockin,rate):
    index, rate = get_closest_value(sample_rates, rate)
    lockin.write(
        'SRAT {:d}'.format(index)
    )
    return rate

def get_sample_rate(lockin):
    return sample_rates[int(lockin.query('SRAT?'))]

def get_sample_rates():
    return sample_rates

def get_frequency(lockin):
    return float(
        lockin.query('FREQ?')
    )

def set_frequency(lockin,frequency):
    lockin.write(
        'FREQ {:f}'.format(frequency)
    )

def get_phase(lockin):
    return float(
        lockin.query('PHAS?')
    )

def set_phase(lockin,phase):
    lockin.write(
        'PHAS {:f}'.format(phase)
    )

def get_mod_amp(lockin):
    return float(
        lockin.query('SLVL?')
    )

def set_mod_amp(lockin,amp):
    lockin.write(
        'SLVL {:f}'.format(amp)
    )

sensitivities = (
    2e-9,5e-9,
    10e-9,20e-9,50e-9,
    100e-9,200e-9,500e-9,
    1e-6,2e-6,5e-6,
    10e-6,20e-6,50e-6,
    100e-6,200e-6,500e-6,
    1e-3,2e-3,5e-3,
    10e-3,20e-3,50e-3,
    100e-3,200e-3,500e-3,
    1e-0
)

def get_sensitivity(lockin):
    return sensitivities[int(lockin.query('SENS?'))]

def set_sensitivity(lockin,sensitivity):
    index, sensitivity = get_closest_value(sensitivities,sensitivity)
    lockin.write(
        'SENS {:d}'.format(index)
    )
    return sensitivity

def start_data_storage(lockin):
    lockin.write('STRT')

def pause_data_storage(lockin):
    lockin.write('PAUS')

def reset_data_storage(lockin):
    lockin.write('REST')

def get_num_samples(lockin):
    return int(lockin.query('SPTS?'))

# note: bus can transfer about 150 samples per second.
# select length or set timeout accordingly
def read_data_storage(lockin,channel,start,length):
    return list(
        map(
            float,
            lockin.query(
                'TRCA ? {:d}, {:d}, {:d}'.format(
                    channel,start,length
                )
            ).split(',')[:-1]
        )
    )

CH1, CH2 = 1, 2
X, R = 0, 1
Y, THETA = 0, 1
def get_display_type(lockin,channel):
    return int(lockin.query('DDEF? {:d}'.format(channel)).split(',')[0])

def set_display_type(lockin,channel,type):
    lockin.write('DDEF {:d}, {:d}, 0'.format(channel,type))

if __name__ == '__main__':
    with LockinHandler() as lockin:
        tau = get_time_constant(lockin)
        print('lockin time constant: {:.1g} seconds'.format(tau))
