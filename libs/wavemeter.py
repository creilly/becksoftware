import pyvisa

wmid = 'wavemeter'

class WavemeterHandler:
    def __init__(self,wmid=wmid):
        self.wm = open_wavemeter(wmid)

    def __enter__(self):
        return self.wm

    def __exit__(self,*args):
        close_wavemeter(self.wm)

def open_wavemeter(wmid=wmid):
    wm = pyvisa.ResourceManager().open_resource(wmid)
    wm.timeout = 500
    # read and discard greeting
    bytes = bytearray(b'')
    while True:
        try:
            bytes.append(wm.read_bytes(1)[0])
        except pyvisa.errors.VisaIOError:
            break
    # print(bytes.decode('utf-8'))    
    wm.timeout = 10000
    wm.write_termination = '\n'
    wm.read_termination = '\r\n'
    wm._model = modeld[int(wm.query('*IDN?').split(', ')[1][:3])]
    # set_wnum_units(wm,WNUM)
    return wm

def close_wavemeter(wm):
    wm.close()

MW, DBM = 0, 1
powunitsd = {
    MW:'MW',
    DBM:'DBM'
}
def set_power_units(wm,units):
    wm.write(':UNIT:POW MW')

WNUM = 0
wnumunitsd = {
    WNUM:'WNUM',
}
def set_wnum_units(wm,units):
    wm.write(':UNIT:WAV WNUM')

_671, _771 = 0, 1

modeld = {
    671:_671,
    771:_771
}

SCANNUM, STATUS, WAVELENGTH, POWER, OSNR = 0, 1, 2, 3, 4

paramsd = {
    _671:(SCANNUM, STATUS, WAVELENGTH, POWER),
    _771:(SCANNUM, STATUS, WAVELENGTH, POWER, OSNR)
}

mapsd = {
    SCANNUM:int,
    STATUS:int,
    WAVELENGTH:float,
    POWER:float,
    OSNR:float
}

NEW, OLD = 0, 1

def parse_sync(sync):
    return {
        NEW:'MEAS',
        OLD:'READ'
    }[sync]

def get_measurement(wm,sync=NEW):
    response = wm.query(
        ':{}:ALL?'.format(
            parse_sync(sync)
        )
    )
    return {
        key:mapsd[key](value)
        for key, value in
        zip(
            paramsd[wm._model],
            response.strip().split(', ')
        )
    }

def get_wavenumber(wm,sync=NEW):
    return float(wm.query(':{}:WNUM?'.format(parse_sync(sync))))

def get_power(wm,sync=NEW):
    return float(wm.query(':{}:POW?'.format(parse_sync(sync))))

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        N = int(sys.argv[1])
    else:
        N = int(input('enter number of samples to average: '))
    print('{:d} sample running average of wavenumber.'.format(N))
    print('press ctrl-c to quit')
    try:
        with WavemeterHandler() as wm:
            wavg = get_wavenumber(wm)
            while True:
                print('wavenumber:','{:.6f}'.format(wavg),'cm-1')
                wnew = get_wavenumber(wm)
                wavg = (N-1) / N * wavg + 1 / N * wnew
    except KeyboardInterrupt:
        print('keyboard interrupt received. exiting...')
