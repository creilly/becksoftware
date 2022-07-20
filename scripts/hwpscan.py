import rotationstage as rot
import gentec as pm
from grapher import graphclient as gc
import numpy as np
import sys
import topo

ic = topo.InstructionClient()

if len(sys.argv) < 3:
    folder = []
else:
    folder = [sys.argv[2]]
if len(sys.argv) < 2:
    name = 'hwp scan'
else:
    name = sys.argv[1]

sn = None
pmh = None 
N = 1
ao = 0.0
with pm.GentecHandler() as pmh, rot.RotationStageHandler() as sn:
    angles = np.arange(ao,ao+90.0,0.5)/1.0

    if not rot.is_homed(sn):
        print('stage not homed. homing...')
        rot.home(sn)

    path = gc.add_dataset(
        gc.get_day_folder() + folder,
        name,
        (
            'hwp angle (degs)',
            'power (watts)',
            'ir photodiode (volts)'
        )
    )

    for angle in angles:
        rot.set_angle(sn,angle)
        power = irpd = n = 0        
        N = 10
        while n < N:
            n += 1
            power += pm.get_power(pmh)
            irpd += ic.get_input(topo.FAST4)
        power /= N
        irpd /= N
        print(angle,power,irpd)
        gc.add_data(path,(angle,power,irpd))
    
