import ipg
from time import time, sleep

DELTAT_SHORT = 180.0 # seconds
DELTAT_LONG = 2400.0
DELTAT_NOW = 0.0

steps = (
    ( 3.0, DELTAT_NOW ),
    ( 6.0, DELTAT_SHORT ),
    ( 8.0, DELTAT_SHORT ),
    ( 10.0, DELTAT_SHORT ),
    ( 12.0, DELTAT_LONG )
)

SLEEP = 1.0

with ipg.IPGHandler() as ipgh:
    for power, DELTAT in steps:
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
            
    
