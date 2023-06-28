import gentec as pm
import pi, time
import numpy as np
from matplotlib import pyplot as plt

deltaz = 2.0 # mm
dz = 0.05
dt = 1.0

positions = {
    axis:{} for axis in (pi.X,pi.Y)
}

with (
        pi.PIHandler() as pih,
        pm.GentecHandler('gentecblu') as pmh
):
    for axis, d in positions.items():
        zo = pi.get_position(pih,axis)
        zs = zo + np.arange(-deltaz/2,+deltaz/2,dz)
        for z in zs:
            pi.set_position(pih,axis,z)
            pi.wait_motor(pih,axis)
            time.sleep(dt)
            pm.start_stream(pmh)
            time.sleep(dt)
            d[z] = pm.stop_stream(pmh)            
            print(
                'z:','{:.3f} mm'.format(z).rjust(15),
                '|',
                'p:','{:.2f} mW'.format(1e3*d[z]).rjust(15)
            )
        zmax = max(d.items(),key=lambda x: x[1])[0]
        print('zmax:','{:.3f} mm'.format(zmax).rjust(15))
        pi.set_position(pih,axis,zmax)
        plt.plot(
            *zip(*d.items()),
            '.',
            label = {
                pi.X:'x',
                pi.Y:'y'
            }[axis]
        )
plt.xlabel('motor position (mm)')
plt.ylabel('transmitted power (watts)')
plt.legend()
plt.show()

            

