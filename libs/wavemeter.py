import pyvisa

wmid = 'wavemeter'
wm = pyvisa.ResourceManager().open_resource(wmid)
wm.timeout = 250
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

_671, _771 = 0, 1

modeld = {
    671:_671,
    771:_771
}

def get_model():
    return modeld[int(wm.query('*IDN?').split(', ')[1][:3])]

model = get_model()

wm.write(':UNIT:POW MW')
wm.write(':UNIT:WAV WNUM')

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

def get_measurement(sync=NEW):
    response = wm.query(
        ':{}:ALL?'.format(
            parse_sync(sync)
        )
    )
    return {
        key:mapsd[key](value)
        for key, value in
        zip(
            paramsd[model],
            response.strip().split(', ')
        )
    }

def get_wavenumber(sync=NEW):
    return float(wm.query(':{}:WNUM?'.format(parse_sync(sync))))

def get_power(sync=NEW):
    return float(wm.query(':{}:POW?'.format(parse_sync(sync))))

def close_wavemeter():
    return wm.close()

if __name__ == '__main__':
    from time import time, sleep
    prevtime = time()
    print('new')
    prevint = 0
    for _ in range(5):
        print('power',get_measurement(NEW))
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
    # print('old')
    # for _ in range(5):
    #     print('power',get_measurement(OLD))
    #     newtime = time()
    #     print(newtime-prevtime)
    #     prevtime = newtime
    #     sleep(1.0)
        
