import ipg
from time import time, sleep

steps = (9.0, 6.0, 3.0, 0.0)

DELTAT = 180.0 # seconds
SLEEP = 1.0

with ipg.IPGHandler() as ipgh:
    for index, power in enumerate(steps):
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
                '{: 3d} s'.format(int(deltat)),
                '/',
                '{: 3d} s'.format(int(DELTAT))
            )
            if deltat > DELTAT or index == 0:
                break
            sleep(SLEEP)
        ipg.set_power_setpoint(ipgh,power)    
