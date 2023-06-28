import ipg, argparse
from time import time, sleep

DELTAT_SHORT = 180.0 # seconds
DELTAT_MEDIUM = 540 
DELTAT_LONG = 2400.0 
DELTAT_NOW = 0.0

steps = (
    ( 3.0, DELTAT_NOW ),
    ( 6.0, DELTAT_SHORT ),
    ( 8.0, DELTAT_SHORT ),
    ( 10.0, DELTAT_SHORT ),
    ( 12.0, DELTAT_LONG ),
    ( 14.0, DELTAT_MEDIUM )
)

SLEEP = 1.0

W12 = 12
W14 = 14
ap = argparse.ArgumentParser()
ap.add_argument('--power','-p',choices=(W12,W14),type=int,default=W12)
maxpower = ap.parse_args().power

with ipg.IPGHandler() as ipgh:
    for power, DELTAT in steps:
        if power > maxpower:
            break
        starttime = time()
        while True:
            currenttime = time()
            deltat = currenttime - starttime
            print(
                'current setpoint:',
                '{:.2f} w'.format(
                    ipg.get_power_setpoint(ipgh)
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
            
    
