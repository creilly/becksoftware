import pi, numpy as np, time, gentec
from grapher import graphclient as gc
import rotationstage as rs

deltaz = 1.25 # mm
dz = 0.025 # mm
dt = 2.0 # seconds
deltat = 4.0 # seconds

theta_start = 15.0
theta_stop = 350.0
dtheta = 5.0

theta = theta_start
axes = (pi.X,pi.Y)

named = {pi.X:'x',pi.Y:'y'}
subfolder = 'hwp mirror calib' # 'lid mirror calib - fixed lid'
rootfolder = [*gc.get_day_folder(),'hwp mirror calib']
with (
    gentec.GentecHandler('gentecblu') as gh,
    rs.RotationStageHandler() as rsh,
    pi.PIHandler() as pih
):
    zos = {
        axis:pi.get_position(pih,axis)
        for axis in axes
    }
    while theta < theta_stop:
        rs.set_angle(rsh,theta)
        for axis in (pi.X,pi.Y):
            aname = named[axis]
            zs = zos[axis] + np.arange(-deltaz/2,+deltaz/2,dz)
            path = gc.add_dataset(
                [*rootfolder,'{: 6d} mdegs'.format(int(round(1000*theta,0)))],
                '{} axis'.format(aname),
                ('{} position (mm)'.format(aname),'transmitted power (watts)'),
                {'axis':aname,'theta':(theta,'degs')}
            )            
            pmax = None            
            pi.set_position(pih,axis,zs[0])
            pi.wait_motor(pih,axis)
            time.sleep(deltat)
            for z in zs:
                pi.set_position(pih,axis,z)
                pi.wait_motor(pih,axis)
                time.sleep(dt)
                gentec.start_stream(gh)
                time.sleep(dt)
                p = gentec.stop_stream(gh)
                if pmax is None or p > pmax:
                    pmax = p
                    zmax = z
                gc.add_data(path,(z,p))
            pi.set_position(pih,axis,zmax)
            pi.wait_motor(pih,axis)
            zos[axis] = zmax
        theta += dtheta        