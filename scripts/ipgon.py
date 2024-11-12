import ipg, argparse
from time import time, sleep

DELTAT_SHORT = 30.0 # seconds
DELTAT_MEDIUM = 30.0 
DELTAT_LONG = 120.0 
DELTAT_NOW = 0.0

steps = (
    ( 3.0, DELTAT_NOW ),
    ( 6.0, DELTAT_SHORT ),
    ( 8.0, DELTAT_SHORT ),
    ( 10.0, DELTAT_SHORT ),
    ( 12.0, DELTAT_LONG ),
    ( 14.0, DELTAT_MEDIUM ),
    ( 15.0, DELTAT_SHORT)
)

SLEEP = 1.0

W12 = 12
W14 = 14
W15 = 15

ap = argparse.ArgumentParser()
ap.add_argument('--power','-p',choices=(W12,W14,W15),type=int,default=W12)
ap.add_argument('--amp','-a',choices=(ipg.A99,ipg.A03),type=int,default=ipg.A03)
apargs = ap.parse_args()
maxpower = apargs.power
amp = apargs.amp

with ipg.IPGHandler(ipg.visad[amp]) as ipgh:
    for power, DELTAT in steps:
        if power > maxpower:
            break
        powero = ipg.get_power_setpoint(ipgh)
        if powero >= power: continue
        starttime = time()
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
                    power
                ).rjust(10),
                ',',
                'time:',
                '{: 4d} s'.format(int(deltat)),
                '/',
                '{: 4d} s'.format(int(DELTAT))
            )
            if deltat > DELTAT:
                break
            sleep(SLEEP)
        ipg.set_power_setpoint(ipgh,power)
        sleep(SLEEP)
            
    
