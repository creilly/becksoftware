from bologain import bologainserver, bologainclient
import maxon
import datetime
import daqmx
import lockin
from time import time, sleep
from transfercavity import transfercavityclient as tcc
from lid import lidclient
from bilt import IH, MA, LI, gcp

SHUTTER_SHUT, SHUTTER_OPEN = False, True
poll_time = 0.25 # seconds
spin_poll_time = 2.0 # seconds
meas_time = 6.0 # seconds
chopped_beam_bolo_gain = bologainserver.X1000
# measured 2022-08-04
# appears to vary (+- 10 degrees) with methane exposure
# and bolometer load.
#
# objective is to synchronize to tagged beam, so error 
# goes as 1 - cos(epsilon_theta) ~ epsilon_theta ** 2
# so for epsilon_theta = 10 degrees, we have 
# error = (10 / 180 * 3.14)^2 ~ 4 percent, which is ok
deltaphi_tagged_chopped = -145.0 # degrees

class TokenEmpty(Exception):
    pass
    
def get_sensitivity(cfg,handlerd,rescon,token):        
    try:
        # token to interrupt handler
        ih = token

        # get handles to hardware and interrupt handler
        lih, mh = handlerd[LI], handlerd[MA]

        # for metrics
        sens_start_time = time()

        # set mol beam chopping frequency 
        # equal to tagging laser chopping frequency
        f_chop = lockin.get_frequency(lih) # hz
        v_chop = f_chop * 60 / 2 # rpm

        # position lid to reference angle
        print('requesting lid positioning to reference angle')
        lid_angle = gcp(cfg,'scattering','lid angle',float)
        lidclient.set_lid(lid_angle,wait=False)

        # start motor spin up
        print('starting up motor')
        check_fault(mh)
        start_spin(mh,v_chop)

        # set lockin sensitivity for chopped beam
        chopped_beam_lia_sens = gcp(cfg,'sensitivity','lockin sensitivity',float)
        lockin.set_sensitivity(lih,chopped_beam_lia_sens)

        print('setting bolo gain to {:d}'.format(chopped_beam_bolo_gain))
        # set bologain to minimum gain
        bologainclient.set_gain(chopped_beam_bolo_gain)    
        
        print('blocking tagging and pumping beams')
        # set NI DAQ box digital lines to shut the shutters
        for channel_name in ('pump shutter', 'tag shutter'):
            with daqmx.LineHandler(channel_name) as line:
                daqmx.write_line(line,SHUTTER_SHUT)

        print('waiting for motor to reach chopping speed...')
        finish_spin(mh,ih,get_spin_cb(v_chop))
        print('chopping speed reached.')

        # set lockin to external
        print('setting lockin to external sync')
        lockin.set_ref_source(lih,lockin.EXTERNAL)

        # wait for lockin to sync
        print('waiting for lockin to sync')
        while lockin.get_unlocked(lih):
            print('lockin unlocked! waiting...')
            check_ih(ih)
            sleep(poll_time)
        print('lockin locked.')

        # wait to lid positioning to complete
        print('waiting for lid move to finish')
        lidclient.wait_lid()
        print('lid in position')

        # wait 10 time constants
        print('waiting for fresh data.')
        sleep(
            gcp(cfg,'lockin','time constant',float)*10
        )
        print('wait completed.')

        # measure signal
        starttime = time()
        R = T = n = 0
        while True:
            check_ih(ih)
            r, t = lockin.get_rt(lih)
            R += r
            if n:
                # handle wrap-around phase errors
                while t - T > 90:
                    t -= 180
                while t - T < -90:
                    t += 180
            n += 1
            T = ((n-1) * T + t)/n        
            if time() - starttime > meas_time:
                break
        R /= n    
        print('sensitivity measurement:')
        print('r : {:.2e} volts'.format(R))
        print('t : {:.2f} degrees'.format(T))

        # rephase the lockin
        # from measurements on 2022-08-04,
        # tagging phase is approximately -35 degrees
        # shifted from chopped phase at 237 Hz
        phio = lockin.get_phase(lih)
        phichopped = phio + T
        phitagged = phichopped + deltaphi_tagged_chopped
        while phitagged <= -360.0:
            phitagged += 180.0
        while phitagged >= 729.99:
            phitagged -= 180.0
        lockin.set_phase(lih,phitagged)
        phip = lockin.get_phase(lih)
        
        # get timestamp for sensitivity measurement
        sens_dt_str = datetime.datetime.now().isoformat()

        # construct metadata for sensitivity measurement
        sens_md = {
            'timestamp':sens_dt_str,
            'measurement':{
                'r':[R,'volts'],
                't':[T,'degrees']
            },
            'chopping frequency':[f_chop,'Hz'],
            'lockin sensitivity':[chopped_beam_lia_sens,'volts'],
            'lockin phase before':[phio,'degrees'],
            'lockin phase after':[phip,'degrees'],
            'bolo gain':[chopped_beam_bolo_gain,'X']        
        }
        rescon.append(sens_md)

        # set lockin to internal mode
        print('setting lockin to internal mode')
        lockin.set_ref_source(lih,lockin.INTERNAL)

        # halt motor
        print('spinning down motor.')
        start_spin(mh,0)
        print('waiting for motor to stop.')
        finish_spin(mh,ih,get_spin_cb(0))
        
        print('stop complete.')
        maxon.set_enabled_state(mh,False)
        
        # home motor
        print('setting motor to homing mode.')
        home_motor(mh,ih)

        print('changing motor to profile position mode')
        # set to profile position mode        
        maxon.set_operation_mode(mh,maxon.M_PROFILE_POSITION)  
        
        print('blocking beam while other operations finish')
        maxon.move_to_position(mh,maxon_closed)

        print('unblocking tagging and pumping beams')
        # set NI DAQ box digital lines to open the shutters
        for channel_name in ('pump shutter', 'tag shutter'):
            with daqmx.LineHandler(channel_name) as line:
                daqmx.write_line(line,SHUTTER_OPEN)            

        print('sensitivity measurement over')
        sens_stop_time = time()
        sens_delta_time = sens_stop_time - sens_start_time
        print('sensitivity measurement time: {:.1f} seconds'.format(sens_delta_time))    
    except TokenEmpty:
        return

maxon_open = 0
maxon_closed = 20
    
def home_motor(mh,ih):
    maxon.set_operation_mode(mh,maxon.M_HOMING)        
    while True:        
        maxon.set_enabled_state(mh,True)
        print('homing motor.')
        maxon.find_home(mh)
        breaking = True
        while True:
            check_ih(ih)
            if check_fault(mh):
                breaking = False
                break
            # get status of homing procedure
            homing_attained, homing_error = maxon.get_homing_state(mh)
            if homing_error:
                raise Exception('homing error')
            if homing_attained:
                print('homing attained.')
                break
            # read current position
            pos = maxon.get_position_act(mh)
            print('position: {:d} steps'.format(pos))
            sleep(poll_time)
        if breaking:
            break

def start_spin(mh,v_chop):
    units = maxon.get_velocity_units(mh)
    maxon.set_operation_mode(mh,maxon.M_PROFILE_VELOCITY)
    maxon.set_enabled_state(mh,True)    
    maxon.move_with_velocity(mh,v_chop,units)

def finish_spin(mh,ih,cb):
    units = maxon.get_velocity_units(mh)
    while not maxon.get_movement_state(mh):        
        if check_fault(mh):
            return get_sensitivity()
        check_ih(ih)
        # read current averaged velocity
        v_act = maxon.get_velocity_act(mh,units)
        cb(v_act)
        sleep(spin_poll_time) 

def get_spin_cb(v_tar):
    def spin_cb(v_act):
        print(
            ',\t'.join(
                '{}: {:.3f} rpm'.format(label,vel)
                for label, vel in (
                        ('vset',v_tar),
                        ('vact',v_act),
                )
            )
        )
    return spin_cb

def check_fault(mh):
    # handle maxon motor faults        
    faulting = maxon.get_fault(mh)        
    if faulting:            
        print('fault detected!')
        print('clearing fault.')
        maxon.clear_fault(mh)
        with open('faultlog.txt','a') as f:
            f.write(datetime.datetime.now().isoformat() + '\n')
    return faulting

def check_ih(ih):
    if not ih:
        raise TokenEmpty()

_print = print
def print(*args):
    _print(' ' * 50,*args)        