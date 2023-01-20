import rotationstage as rot
import gentec as pm
from grapher import graphclient as gc
import numpy as np
from time import time, sleep
import topo
import argparse
import wavemeter

ap = argparse.ArgumentParser(description='hwp scanning program')
ap.add_argument('--name','-n',default='hwp scan',help='grapher dataset name')
ap.add_argument('--time','-t',default=1.0,type=float,help='time per measurement')
ap.add_argument('--settle','-l',default=1.0,type=float,help='settle time')
ap.add_argument('--step','-s',type=float,default=2.0,help='step size (degrees)')
ap.add_argument('--min','-m',default=10.0,type=float,help='starting angle')
ap.add_argument('--max','-p',default=65.0,type=float,help='stopping angle')
ap.add_argument(
    '--folder','-f',default=gc.get_day_folder(),nargs='*',
    help='grapher folder. enclose each subfolder in quotes and separate by whitespace.'
)
ap.add_argument('--info','-i',default='',help='dataset metadata note')

args = ap.parse_args()
name = args.name
meastime = args.time
anglestep = args.step
anglemin = args.min
anglemax = args.max
folder = args.folder
info = args.info
settle = args.settle

ic = topo.InstructionClient()

with pm.GentecHandler() as pmh, rot.RotationStageHandler() as sn, wavemeter.WavemeterHandler() as wmh:
    pm.set_autoscale(pmh,False)
    sleep(1.0)
    pm.set_range(pmh,pm.RANGE_1W)
    sleep(1.0)
    w = wavemeter.get_wavenumber(wmh)
    angles = np.arange(anglemin,anglemax,anglestep)

    if not rot.is_homed(sn):
        print('stage not homed. homing...')
        rot.home(sn)

    path = gc.add_dataset(
        folder,
        name,
        (
            'hwp angle (degs)',
            'power (watts)',
            'ir photodiode (volts)'
        ),
        metadata = {'wavelength':(w,'cm-1'),**({'info':info} if info else {})}
    )

    for angle in angles:
        rot.set_angle(sn,angle)
        sleep(settle)
        starttime = time()
        pm.start_stream(pmh)
        irpd = n = 0                
        while True:
            n += 1            
            irpd += ic.get_input(topo.FAST4)
            if time() - starttime > meastime:
                break                
        irpd /= n
        power = pm.stop_stream(pmh)
        print(angle,power,irpd)
        gc.add_data(path,(angle,power,irpd))