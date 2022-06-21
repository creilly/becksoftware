import pyvisa
from sympy import arg

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

NEW, OLD, FETCH = 0, 1, 2

def parse_sync(sync):
    return {
        NEW:'MEAS',
        OLD:'READ',
        FETCH:'FETCH'
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

class AsyncWavenumber:    
    def __init__(self,wm):
        self.wm = wm
        self.prev_sn = self.get_sn()
        self.wm = wm

    def get_sn(self):
        return get_measurement(self.wm,FETCH)[SCANNUM]

    def _get_wavenumber(self):
        return get_wavenumber(self.wm,FETCH)

    def get_wavenumber(self):
        sn = self.get_sn()
        if sn > self.prev_sn:
            return True, self._get_wavenumber()
        else:
            return False, None

def get_wavenumber(wm,sync=NEW):
    return float(wm.query(':{}:WNUM?'.format(parse_sync(sync))))

def get_power(wm,sync=NEW):
    return float(wm.query(':{}:POW?'.format(parse_sync(sync))))

if __name__ == '__main__':
    import sys
    from time import sleep
    import argparse
    parser = argparse.ArgumentParser(description='bristol wavemeter utility')
    parser.add_argument(
        '-w','--wavemeter',default='wavemeter',
        choices=['wavemeter','argos-wavemeter'],
        help='visa id of wavemeter'
    )
    parser.add_argument(
        '-n','--samples',
        default=1,type=int,
        help='number of samples to average per measurement'
    )
    args = parser.parse_args()
    wmid = args.wavemeter
    N = args.samples
    print('{:d} sample running average of wavenumber.'.format(N))
    print('press ctrl-c to quit')
    try:
        print('opening wavemeter with visa id {}'.format(wmid))
        with WavemeterHandler(wmid) as wm:
            print('async test')
            cb = AsyncWavenumber(wm)
            while True:
                ready, w = cb.get_wavenumber()                
                if ready:
                    print('got new w,','{:.4f} cm-1'.format(w))
                    break
                else:
                    print('still waiting')
                    sleep(0.05)
            wavg = get_wavenumber(wm)
            while True:
                print('wavenumber:','{:.6f}'.format(wavg),'cm-1')
                wnew = get_wavenumber(wm)
                wavg = (N-1) / N * wavg + 1 / N * wnew
    except KeyboardInterrupt:
        print('keyboard interrupt received. exiting...')
