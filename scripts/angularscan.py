from bologain import bologainserver, bologainclient
from lid import lidclient
import lockin
import config
from grapher import graphclient as gc
from time import sleep, time
import numpy as np
import argparse
import interrupthandler

def_bolo_sens = 200.0e-3

ap = argparse.ArgumentParser()
ap.add_argument('-s','--bolosens',type=float,default=def_bolo_sens,help='bolometer sensitivity')

args = ap.parse_args()

bolo_sens = args.bolosens
lockin_tau = 100e-3

with lockin.LockinHandler() as lih:
    lockin.set_time_constant(lih,lockin_tau)
    lockin.set_sensitivity(lih,bolo_sens)

centerangle = float(input('enter the center lid angle: '))

bologain = bologainserver.X10

theta_lim = 48.0

delta_theta = 4.0
theta_spec = centerangle
theta_min = max(theta_lim,theta_spec-delta_theta)
theta_max = theta_spec+delta_theta
    
dtheta = 0.5

thetas = np.arange(theta_min,theta_max + dtheta/2,dtheta)

wait_time = 1.0

measure_time = 1.0

folder = gc.get_day_folder() + ['lidscan']

fname = input('enter description: ')

bologainclient.set_gain(bologain)

metadata = config.get_metadata([config.LOGGER,config.LOCKIN,config.BOLOMETER])
startscantime = time()
metadata['start time'] = (startscantime,'seconds since epoch')

path = gc.add_dataset(
    folder,
    fname,
    (
        'lid angle (degrees)',
        'lockin r (volts)',
        'lockin theta (degrees)',
        'time delta since start time(s)'        
    ),
    metadata = metadata
)

with (
    lockin.LockinHandler() as lih,
    interrupthandler.InterruptHandler() as ih
):
    print('press ctrl-c to quit.')
    
    for theta in thetas:
        if ih.interrupt_received():
            print('interrupt received. quitting.')
            break
        print('angle:',int(1000*theta),'milldegrees')
        lidclient.set_lid(theta)
        print('waiting to stabilize...')
        sleep(wait_time)
        lidclient.wait_lid(lambda : print(lidclient.get_lid()))
        R = T = DT = 0
        n = 0
        start_time = time()
        while True:
            r, t = lockin.get_rt(lih)
            R += r
            T += t
            DT += time()-startscantime
            n += 1
            if time()-start_time > measure_time:
                break
        R /= n
        T /= n
        DT /=n        
        gc.add_data(path,(theta,R,T,DT))