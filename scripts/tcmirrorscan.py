import tclock as tl
from tc import tcclient as tcc
from grapher import graphclient as gc
import lockin
import config
from time import time
from time import sleep
import numpy as np
import mirrormotion as mm
import pi
import topo
import math

transition = input('enter tagging transition: ')

lidangle = float(input('enter center mirror angle: '))

fmod = {
    'y':True, 'n':False
}[input('frequency modulating? y or n: ').strip().lower()[0]]

fshift = 50.0 # MHz

delta_theta = 6.0

theta_min = lidangle-delta_theta
theta_max = lidangle+delta_theta
dtheta = 0.5

phis = np.arange(theta_min,theta_max + dtheta/2,dtheta)

wsp = config.get_wavesource_params()
lip = config.get_lockin_params()

with (
        pi.PIHandler() as pih,
        lockin.LockinHandler() as lih
):    
    ic = topo.InstructionClient()
    meastime = lockin.get_time_constant(lih) * 10
    name = transition
    fmax = tcc.get_setpoint()
    fmin = fmax + (
        -1 if fmax > 0 else + 1
    ) * fshift
    path = gc.add_dataset(
        gc.get_day_folder() + ['mirror bolo calib'],
        name,
        (
            'mirror angle (degs)',
            'lockin x on res (v)',
            'lockin y on res (v)',
            'pd on res (v)',
            'lockin x off res (v)',
            'lockin y off res (v)',
            'pd off res (v)',
        ),
        metadata = {
            'fmod':fmod,
            **config.get_metadata(lih)
        }
    )
    for phiindex, phi in enumerate(phis):
        tcc.set_setpoint(fmax)
        mm.set_mirrors(pih,phi)            
        data = [phi]        
        for resindex, f in enumerate(
            (
                fmax,*([fmin] if fmod else [])
            )
        ):
            if resindex and not fmod:
                tcc.set_setpoint(f)            
            sleep(meastime)
            x, y = lockin.get_xy(lih)
            pd = ic.get_input(topo.FAST4)        
            data.extend([x,y,pd])
            if fmod:
                data.extend([math.nan]*3)
                continue
        gc.add_data(path,data)