import pyvisa
import numpy as np

scopeid = 'oscilloscope'

scope = None

class ScopeHandler:
    def __init__(self,scodeid=scopeid):
        self.scope = open_scope(scopeid)

    def __enter__(self):
        return self.scope

    def __exit__(self,*args):
        close_scope(self.scope)

def open_scope(scopeid=scopeid):
    scope = pyvisa.ResourceManager().open_resource(scopeid)
    scope.timeout = 1500
    return scope
    
def close_scope(scope):
    scope.close()

def set_dc_output(scope,voltage):
    scope.write('vbs app.WaveSource.Offset = {:.6f}'.format(voltage))

def set_wavesource_enabled(scope,enabled):
    scope.write(
        'vbs app.WaveSource.Enable = {:d}'.format(
            {
                True:-1,
                False:0
            }[enabled]
        )
    )

def get_wavesource_enabled(scope):
    return bool(
        int(
            scope.query('vbs? \'return = app.WaveSource.Enable\'').strip().split(' ')[-1]
        )
    )

SINE, SQUARE, TRIANGLE, PULSE, DC, NOISE, ARB = 0, 1, 2, 3, 4, 5, 6
def set_wavesource_shape(scope,shape):
    scope.write(
        'vbs app.WaveSource.Shape = {:d}'.format(shape)
    )
shaped = {
    'Sine':SINE,'Square':SQUARE,'Triangle':TRIANGLE,
    'Pulse':PULSE,'DC':DC,'Noise':NOISE,'ARB':ARB
}
def get_wavesource_shape(scope):
    return scope.query('vbs? \'return = app.WaveSource.Shape\'').strip().split(' ')[-1]

def set_rms_noise(scope,vrms):
    scope.write('vbs app.WaveSource.StdDev = {:.6f}'.format(vrms))

def get_rms_noise(scope):
    return float(scope.query('vbs? \'return = app.WaveSource.StdDev\'').split(' ')[-1])

def get_trace(scope,channel):
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

def get_trace_info(scope,channel):
    rawinfo = scope.query('{}:INSP? \'WAVEDESC\',FLOAT'.format(channel)).strip()[1:-1].strip()
    info = {
        key.strip():':'.join(values).strip() for key,*values in [
            line.split(':') for line in rawinfo.split('\n')
        ]
    }
    return info

def get_horizontal_interval(scope,channel):
    return float(get_trace_info(channel)['HORIZ_INTERVAL'])

def get_horizontal_offset(scope,channel):
    return float(get_trace_info(channel)['HORIZ_OFFSET'])

AUTO, NORM, SINGLE, STOP = 'AUTO', 'NORM', 'SINGLE', 'STOP'
def set_trigger_mode(scope,mode):
    scope.write('TRMD {}'.format(mode))

def arm_trigger(scope):
    scope.write('ARM')

def send_command(scope,command):
    scope.write(command)

def send_query(scope,query):
    return scope.query(query)

def clear_sweeps(scope):
    scope.write('CLSW')

def wait(scope):
    scope.write('WAIT')

def show_trace(scope,channel,show):
    scope.write(
        '{}:TRACE {}'.format(
            channel,
            {True:'ON',False:'OFF'}[show]
        )
    )

def get_measurement(scope,channel,measurement):
    return float(
        scope.query(
            '{}:PAVA? {}'.format(channel,measurement)
        ).split(',')[1]
    )

VER, HOR = 0, 1
def set_cursors(scope,mode,c1,c2):
    scope.write(
        'CRST {0}ABS,{1:f},{0}DIF,{2:f}'.format(
            {VER:'V',HOR:'H'}[mode],c1,c2
        )
    )

if __name__ == '__main__':
    with ScopeHandler() as scope:
        vrmso = get_rms_noise(scope)
        vrmsp = vrmso+.1
        print('vrmso',vrmso)
        print('setting vrms to vrmsp = {:e}'.format(vrmsp))
        set_rms_noise(scope,vrmsp)
        print('vrmsp measured',get_rms_noise(scope))
        print('setting vrms to vrmso = {:e}'.format(vrmso))
        set_rms_noise(scope,vrmso)
        print('vrmso measured',get_rms_noise(scope))
              
      
