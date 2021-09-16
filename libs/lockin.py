import pyvisa

LOCKIN_VISA_NAME = 'bilt-lockin'

def load_lockin(name=LOCKIN_VISA_NAME):
    return pyvisa.ResourceManager().open_resource(name)

def load_lockin_preset(lockin,preset_number):
    lockin.write('RSET {:d}'.format(preset_number))

def read_lockin(lockin):
    return float(lockin.query('OUTP ? 1').strip())

def get_xy(lockin):
    return list(map(float,lockin.query('SNAP?1,2').split(',')))

# in hz
def set_frequency(lockin,frequency):
    lockin.write('FREQ {:f}'.format(frequency))

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
    lockin = load_lockin()
    load_lockin_preset(lockin,2)
    print(read_lockin(lockin))
    close_lockin(lockin)
