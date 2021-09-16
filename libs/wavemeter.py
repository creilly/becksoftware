import pyvisa

wmid = 'wavemeter'

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
    from time import time, sleep
    prevtime = time()
    print('new')
    prevint = 0
    try:
        wm = open_wavemeter()
        for _ in range(5):
            print('power',get_measurement(wm,NEW))
            newtime = time()
            newint = newtime - prevtime
            print(newint,newint+prevint)        
            prevint = newint
            prevtime = newtime
            sleep(.2)
            newtime = time()
            newint = newtime - prevtime
            print(newint,newint+prevint)        
            prevint = newint
            prevtime = newtime
    except Exception as e:
        print('error!')
        print(repr(e))
        close_wavemeter(wm)
        
