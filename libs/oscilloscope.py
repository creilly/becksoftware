import pyvisa
import numpy as np

scopeid = 'oscilloscope'

scope = pyvisa.ResourceManager().open_resource(scopeid)

scope.timeout = 1500

def set_dc_output(voltage):
    scope.write('vbs app.WaveSource.Offset = {:.3f}'.format(voltage))

def get_trace(channel):
    while True:
        try:
            response = scope.query('{}:INSP? \'DATA_ARRAY_1\',FLOAT'.format(channel)).strip()[1:-1].strip()
            print('trace acquired')
            break
        except pyvisa.errors.VisaIOError:
            print('trace acquisition failed. reattempting.')
    return np.hstack(
        [
            [
                float(s) for s in line.split('  ')
            ] for line in response.split('\r\n  ')
        ]
    )

def get_trace_info(channel):
    rawinfo = scope.query('{}:INSP? \'WAVEDESC\',FLOAT'.format(channel)).strip()[1:-1].strip()
    info = {
        key.strip():':'.join(values).strip() for key,*values in [
            line.split(':') for line in rawinfo.split('\n')
        ]
    }
    return info

def get_horizontal_interval(channel):
    return float(get_trace_info(channel)['HORIZ_INTERVAL'])

def get_horizontal_offset(channel):
    return float(get_trace_info(channel)['HORIZ_OFFSET'])

AUTO, NORM, SINGLE, STOP = 'AUTO', 'NORM', 'SINGLE', 'STOP'
def set_trigger_mode(mode):
    scope.write('TRMD {}'.format(mode))

def arm_trigger():
    scope.write('ARM')

def send_command(command):
    scope.write(command)

def send_query(query):
    return scope.query(query)

def clear_sweeps():
    scope.write('CLSW')

def wait():
    scope.write('WAIT')

def show_trace(channel,show):
    scope.write(
        '{}:TRACE {}'.format(
            channel,
            {True:'ON',False:'OFF'}[show]
        )
    )

def get_measurement(channel,measurement):
    return float(
        scope.query(
            '{}:PAVA? {}'.format(channel,measurement)
        ).split(',')[1]
    )

VER, HOR = 0, 1
def set_cursors(mode,c1,c2):
    scope.write(
        'CRST {0}ABS,{1:f},{0}DIF,{2:f}'.format(
            {VER:'V',HOR:'H'}[mode],c1,c2
        )
    )

if __name__ == '__main__':
    print(
        get_trace_info('C3')
    )
      
