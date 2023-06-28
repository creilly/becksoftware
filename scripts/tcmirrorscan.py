import tclock as tl
from transfercavity import transfercavityclient as tcc
from grapher import graphclient as gc
import lockin
import config
from time import time
from time import sleep
import numpy as np
import mirrormotion as mm
import pi
import topo

transition = input('enter tagging transition: ')

lidangle = float(input('enter center mirror angle: '))

fshift = 50.0 # MHz

meastimefc = 1.0

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
    tau = lockin.get_time_constant(lih)
    for _ in (None,):
        def get_lockin(meastime):
            starttime = time()
            X = Y = PD = 0
            n = 0
            while True:
                x, y, pd = lockin.get_xya(lih)
                pd = topo.InstructionClient().get_input(topo.FAST4)
                X += x
                Y += y
                PD += pd
                n += 1 
                if time() - starttime > meastime:
                    break
            X /= n
            Y /= n
            PD /= n
            return X, Y, PD
        metadata = {
            'wavesource':wsp,
            'lockin':lip,
            'transition':transition
        }
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
                'delta lockin r (v)',
                'delta lockin x (v)',
                'delta lockin y (v)',
                'ir photodiode off res (v)'                 
            ),
            metadata = metadata
        )
        for phiindex, phi in enumerate(phis):
            tcc.set_setpoint(fmax)
            mm.set_mirrors(pih,phi)            
            X = Y = 0.0            
            for resindex, f in enumerate(
                (
                    fmax,fmin
                )
            ):
                if resindex:
                    tcc.set_setpoint(f)
                tcc.check_transfer_cavity(f,1.0)                
                sleep(tau * 10.0)
                x, y, pd = get_lockin(meastimefc)
                sign = {0:+1,1:-1}[resindex]                
                X += sign * x
                Y += sign * y
            R = np.sqrt(X**2 + Y**2)
            gc.add_data(path,[phi,R,X,Y,pd])