from bologain import bologainserver, bologainclient
from lid import lidclient
import lockin
import config
from grapher import graphclient as gc
from time import sleep, time
import numpy as np
import argparse
import interrupthandler
import maxon
import datetime

epsilonv = 50 # rpm

def_bolo_sens = 100.0e-3
# def_bolo_sens = 200.0e-3

ap = argparse.ArgumentParser()
ap.add_argument('-s','--bolosens',type=float,default=def_bolo_sens,help='bolometer lockin sensitivity')

args = ap.parse_args()

bolo_sens = args.bolosens
lockin_tau = 30e-3

with lockin.LockinHandler() as lih:
    lockin.set_time_constant(lih,lockin_tau)
    lockin.set_sensitivity(lih,bolo_sens)
    lockin.set_ref_source(lih,lockin.EXTERNAL)

bologain = bologainserver.X200

delta_theta = 1.0
theta_min = 45
theta_max = 90

dtheta = 2.0

thetas = np.arange(theta_min,theta_max + dtheta/2,dtheta)

wait_time = 1.0

measure_time = 1.0
maxon_open = 0
f_chop = 237 #Hz

folder = gc.get_day_folder() + ['lidscan']

fname = input('enter description: ')

bologainclient.set_gain(bologain)

with (
    lockin.LockinHandler() as lih,
    interrupthandler.InterruptHandler() as ih,
    maxon.MaxonHandler() as mh,
):
    print('press ctrl-c to quit.')

    def check_fault():
        # handle maxon motor faults        
        faulting = maxon.get_fault(mh)        
        if faulting:            
            print('fault detected!')
            print('clearing fault.')
            maxon.clear_fault(mh)
            with open('faultlog.txt','a') as f:
                f.write(datetime.datetime.now().isoformat() + '\n')
        return faulting

    check_fault()
    units = maxon.get_velocity_units(mh)
    maxon.set_operation_mode(mh,maxon.M_PROFILE_VELOCITY)
    maxon.set_enabled_state(mh,True)
    v_chop = f_chop * 60 / 2 # rpm
    maxon.move_with_velocity(mh,v_chop,units)
    sleep(5)
    v_act = maxon.get_velocity_act(mh,units)
    print('waiting for motor to reach chopping speed...')
    while abs(v_act-v_chop) > epsilonv:
        v_act = maxon.get_velocity_act(mh,units)
        print(
                    ',\t'.join(
                        '{}: {:.3f} rpm'.format(label,vel)
                        for label, vel in (
                                ('vset',v_chop),
                                ('vact',v_act),
                        )
                    )
                )   
        sleep(2)         
    print('chopping speed reached.')

    separation_valve = input('open separation valve, press enter when done')

    metadata = config.get_metadata(lih,[config.LOGGER,config.LOCKIN,config.BOLOMETER])
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

    print('quick stopping motor.')
    maxon.set_quick_stop_state(mh)
    print('waiting for motor to stop.')
    while not maxon.get_movement_state(mh):
        if check_fault():
            break
        print(
                    'slowing down. vel act:',
                    maxon.get_velocity_act(mh,units),
                    'rpm'
                )
        sleep(5)
        continue
    print('quick stop complete.')
    maxon.set_enabled_state(mh,False)
    separation_valve = input('close separation valve, press enter when done')
    print('setting motor to homing mode.')
    maxon.set_operation_mode(mh,maxon.M_HOMING)        
    
    maxon.set_enabled_state(mh,True)
    print('homing motor.')
    maxon.find_home(mh)    

