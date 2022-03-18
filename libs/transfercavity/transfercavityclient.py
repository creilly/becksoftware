import beckhttpclient as bhc
from . import transfercavityserver as tcs
import base64
import struct

host = '127.0.0.1'
port = tcs.PORT

def send_command(command,params={}):
    return bhc.send_command(host,port,command,params)

def get_lock_output():
    return send_command('get lock output')

def get_setpoint():
    return send_command('get setpoint')

def set_setpoint(setpoint):
    return send_command('set setpoint',{'setpoint':setpoint})

def get_locking():
    return send_command('get locking')

def set_locking(locking):
    return send_command('set locking',{'locking':locking})

def get_offset():
    return send_command('get offset')

def set_offset(offset):
    return send_command('set offset',{'offset':offset})

def zero_offset():
    return send_command('zero offset')

def get_samples(maxindex):
    return send_command('get samples',{'maxindex':maxindex})

def get_scanning():
    return send_command('get scanning')

def set_scanning(scanning):
    return send_command('set scanning',{'scanning':scanning})

def get_scan_index():
    return send_command('get scan index')

def get_scan():
    return {
        key:(decode_scan(b64scan),params)
        for key, (b64scan, params) in send_command('get scan').items()
    }

def get_x():
    return decode_scan(send_command('get x'))

def get_fitting(channel):
    return send_command('get fitting',{'channel':channel})

def set_fitting(channel,fitting):
    return send_command('set fitting',{'channel':channel,'fitting':fitting})

def reset_fitting(channel):
    return send_command('reset fitting',{'channel':channel})

def get_fit_parameters(channel):
    return send_command('get fit parameters',{'channel':channel})

def get_heating():
    return send_command('get heating')

def set_heating(heating):
    return send_command('set heating',{'heating':heating})

def get_heater_voltage():
    return send_command('get heater voltage')

def set_heater_voltage(voltage):
    return send_command('set heater voltage',{'voltage':voltage})

def decode_scan(b64scan):
    bs = base64.b64decode(b64scan.encode())
    return struct.unpack(
        '{:d}f'.format(len(bs)//4),
        bs
    )

if __name__ == '__main__':
    from . import transfercavityserver as tcs
    print('lock setpoint: {:.3f} MHz'.format(get_setpoint()))
    # from matplotlib import pyplot as plt
    # import numpy as np
    # from time import sleep
    # wait = 0.25 # seconds
    # famp = 10.0 # MHz
    # df = 0.1 # MHz
    # N = 4 * int(famp / df)
    # ns = np.arange(N)
    # fs = famp * np.sin(2. * np.pi * ns / N)
    # fexps = []
    # scanindex = -1
    # for n,f in zip(ns,fs):
    #     set_setpoint(f)
    #     sleep(wait)
    #     while True:
    #         samples = get_samples(scanindex)
    #         if samples:
    #             break            
    #     sample = samples[-1]
    #     scanindex = sample[tcs.SCANINDEX]
    #     fexp = sample[tcs.DELTAF]
    #     fexps.append(fexp)
    #     print(n,f,fexp)
    # plt.plot(ns,fs)
    # plt.plot(ns,fexps,'.')
    # plt.show()
