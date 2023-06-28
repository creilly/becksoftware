import pi, gentec, numpy as np, time
from grapher import graphclient as gc
from lid import lidclient as lc

deltaz = 1.5 # mm
dz = 0.1 # mm
dt = 2.0 # seconds
deltat = 4.0 # seconds

theta_start = 111.0
theta_stop = 131.0
dtheta = 1.0

theta = theta_start
axes = (pi.X,pi.Y)

named = {pi.X:'x',pi.Y:'y'}
subfolder = 'lid mirror calib' # 'lid mirror calib - fixed lid'
rootfolder = [*gc.get_day_folder(),'lid mirror calib']
with (
    pi.PIHandler() as pih,
    gentec.GentecHandler('gentecblu') as gh
):
    zos = {
        axis:pi.get_position(pih,axis)
        for axis in axes
    }
    while theta < theta_stop:
        lc.set_lid(theta)
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