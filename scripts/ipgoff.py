import ipg, argparse
from time import time, sleep

ap = argparse.ArgumentParser()
ap.add_argument('--amp','-a',choices=(ipg.A99,ipg.A03),type=int,default=ipg.A03)
apargs = ap.parse_args()
amp = apargs.amp

step = 2.0

DELTAT = 30.0 # seconds
SLEEP = 1.0

with ipg.IPGHandler(ipg.visad[amp]) as ipgh:
    while True:
        starttime = time()
        powero = ipg.get_power_setpoint(ipgh)
        powerp = max(powero - step,0)        
        while True:
            currenttime = time()
            deltat = currenttime - starttime
            print(
                'current setpoint:',
                '{:.2f} w'.format(
                    powero
                ).rjust(10),
                ',',
                'next setpoint:',
                '{:.2f} w'.format(
                    powerp
                ).rjust(10),
                ',',
                'time:',
                '{: 3d} s'.format(int(deltat)),
                '/',
                '{: 3d} s'.format(int(DELTAT))
            )
            if deltat > DELTAT:
                break
            sleep(SLEEP)
        ipg.set_power_setpoint(ipgh,powerp)
        if powerp == 0:
            break
        sleep(SLEEP)
