import rotationstage as rot
import gentec as pm
from grapher import graphclient as gc
import numpy as np
from time import time, sleep
import topo
import argparse
import wavemeter
import lockin

T_CUBE, K_CUBE = 't', 'k'
PUMP, TAG = 'p', 't'
ap = argparse.ArgumentParser(description='hwp scanning program')
ap.add_argument('--name','-n',default='hwp scan',help='grapher dataset name')
ap.add_argument('--time','-t',default=1.0,type=float,help='time per measurement')
ap.add_argument('--settle','-l',default=1.0,type=float,help='settle time')
ap.add_argument('--step','-s',type=float,default=2.0,help='step size (degrees)')
ap.add_argument('--min','-m',default=10.0,type=float,help='starting angle')
ap.add_argument('--max','-p',default=65.0,type=float,help='stopping angle')
ap.add_argument('--sensitivity','-v',default=pm.RANGE_3W,type=float,help='power meter range (in watts for pm, volts for li)')
ap.add_argument(
    '--folder','-f',default=gc.get_day_folder(),nargs='*',
    help='grapher folder. enclose each subfolder in quotes and separate by whitespace.'
)
ap.add_argument('--cube','-c',choices=(K_CUBE,T_CUBE),default='k',help='motor drive model ([k]-cube or [t]-cube)')
ap.add_argument('--info','-i',default='',help='dataset metadata note')
ap.add_argument('--laser','-z',choices=(TAG,PUMP),default=TAG,help='laser, [t]agging or [p]ump (determines wavemeter to read)')
LOCKIN, POWERMETER = 'l', 'p'
ap.add_argument(
    '--detector','-d',
    choices=(LOCKIN,POWERMETER),
    default=POWERMETER,
    help='detector ([l]ockin or [p]owermeter)'
)
args = ap.parse_args()
detector = args.detector
name = args.name
meastime = args.time
anglestep = args.step
anglemin = args.min
anglemax = args.max
folder = args.folder
info = args.info
settle = args.settle
sensitivity = args.sensitivity
cube = args.cube
laser = args.laser

ic = topo.InstructionClient()

while anglemin > anglemax:
    anglemin -= 360

with (
    lockin.LockinHandler() as lih,
    pm.GentecHandler() as pmh,
    rot.RotationStageHandler(
        typeid={
            K_CUBE:rot.KCUBE_DC_SERVO,
            T_CUBE:rot.TCUBE_DC_SERVO
        }[cube]
    ) as sn, 
    wavemeter.WavemeterHandler(
        {
            TAG:'wavemeter',
            PUMP:'argos-wavemeter'
        }[laser]
    ) as wmh
):
    if detector == POWERMETER:
        dh = pmh
        pm.set_autoscale(dh,False)
        sleep(1.0)
        pm.set_range(dh,sensitivity)
        sleep(1.0)
    if detector == LOCKIN:
        dh = lih
        lockin.set_sensitivity(dh,sensitivity)
        lockin.set_time_constant(dh,meastime/10)
    w = wavemeter.get_wavenumber(wmh)
    angles = np.arange(anglemin,anglemax,anglestep)

    if not rot.is_homed(sn):
        print('stage not homed. homing...')
        rot.home(sn)

    path = gc.add_dataset(
        [*folder,'hwp calibs'],
        name,
        (
            'hwp angle (degs)',
            *{
                POWERMETER:('power (watts)','ir photodiode (volts)'),
                LOCKIN:('lockin x voltage (volts)','lockin y voltage (volts)')
            }[detector],        
        ),
        metadata = {'wavelength':(w,'cm-1'),**({'info':info} if info else {})}
    )

    for angle in angles:        
        rot.set_angle(sn,angle)
        sleep(settle)
        starttime = time()
        if detector == POWERMETER:
            pm.start_stream(dh)
            y = n = 0                
            while True:
                n += 1            
                y += ic.get_input(topo.FAST4)
                if time() - starttime > meastime:
                    break                
            y /= n
            x = pm.stop_stream(dh)
        if detector == LOCKIN:
            while time() - starttime < meastime:
                continue
            x, y = lockin.get_xy(dh)
        print(
            ', '.join(
                '{}: {} {}'.format(
                    label, '{:+.2e}'.format(value).rjust(10), units
                ) for label, value, units in zip(
                    (
                        'hwp', *(
                            ('x','y') if 
                            detector == LOCKIN
                            else ('pm','pd')
                        )
                    ), (angle,x,y), (
                        'degs', *(
                            ['v'] * 2 if 
                            detector == LOCKIN
                            else ('w','v')
                        )
                    )
                )
            )
        )
        gc.add_data(path,(angle,x,y))