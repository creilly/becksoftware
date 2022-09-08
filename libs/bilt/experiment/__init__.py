from bilt.experiment.fluencecurve import get_fluence_curve
from maxon import M_PROFILE_POSITION
from bilt.experiment.frequencyscan import scan_frequency
from interrupthandler import InterruptException
from bilt.experiment.modehop import ModeHopDetected
import topo
import hitran
import config
from bologain import bologainclient, bologainserver
from grapher import graphclient as gc
import powercalib
import lockin
import emfile as emf
import rotationstage as rs
import lockin
import pi
import wavemeter as wm
import maxon
import interrupthandler
import mirrormotion as mm
import tclock
from bilt import gcp, RS, LI, PI, AWM, MA, IH, get_wavemeter_offset
from bilt.experiment.chopped import get_sensitivity, maxon_open, maxon_closed, start_spin, finish_spin, get_spin_cb, home_motor
from bilt.experiment.hwp import set_hwp
from bilt.experiment.grapher import create_dataset, namer, LS, FS, FC, AS
from bilt.experiment.linesearch import search_line, OUT_OF_RANGE_ERROR
from bilt.experiment.angularscan import get_angular_scan
import threading
from time import time

def run_experiment(config_fname):
    # load config file into memory from disk
    cfg = config.get_config(config_fname)

    # configure hardware as specified by config file
    initialize(cfg)

    # # get dictionary of hardware parameters that we 
    # # want to query at start of experiment
    # # and store in metadata
    # initcfgd = get_initial_config()

    # get the appropriate set of hwp angles for fluence curves
    phis = get_phis(cfg)   

    # load desired lines to measure
    lines = get_lines(cfg)
    
    with (
        rs.RotationStageHandler() as rsh,
        lockin.LockinHandler() as lih,        
        pi.PIHandler() as pih,
        wm.WavemeterHandler('argos-wavemeter') as awmh,
        maxon.MaxonHandler() as mh,
        interrupthandler.InterruptHandler() as ih,    
    ):
        try:
            handlerd = {
                RS:rsh,LI:lih,PI:pih,AWM:awmh,MA:mh,IH:ih
            }
            # measure all desired lines    
            for line in lines:
                measure_line(line,cfg,phis,handlerd)
        finally:
            block_molecular_beam(handlerd)

SUCCESS, QUIT, RESET, CONTINUE = 0, 1, 2, 3
commandd = {
    QUIT:'q',RESET:'r',CONTINUE:'c'
}
def measure_line(line,cfg,phis,handlerd):
    breaking = False
    trial = 0
    need_ref = not trial    
    while True:                
        print('starting set line trial {:d}'.format(trial))
        end_tagging(handlerd)
        token = [None]
        try:   
            hwp_promise = start_hwp_init(cfg,handlerd,phis[0])
            if need_ref:
                print('first trial, taking chopped beam measurement.')
                sens_promise = start_sensitivity(cfg,handlerd,token)
            print('setting line')
            e, m, fo, wo = set_line(cfg,handlerd,line)
            # e, m, fo, wo = 700, 8.1, 0.0, 3028.7416
            print('line set.')            
            print(
                'line',hitran.fmt_line(line[0]), 
                'e', e, 'm', m, 'fo', fo, 'wo', wo
            )
            if need_ref:
                print('waiting for sensitivity measurement')
                sens_md = end_thread(sens_promise)
                need_ref = False
                print('sentivity measurement complete.')
            print('waiting for hwp / mirror init')
            deltax, deltay = end_thread(hwp_promise)
            print('hwp / mirror init complete.')                        
            print(
                ', '.join(
                    [
                        'delta {}: {:.3f} mm'.format(label,value)
                        for label, value in (('x',deltax),('y',deltay))
                    ]
                )
            )
        except interrupthandler.InterruptException:
            print('interrupt received during line set.')
            print('notifying thread(s) of interrupt.')
            token.pop()
            print('waiting for threads to complete')
            print('waiting for hwp thread')
            hwpthread, _ = hwp_promise
            hwpthread.join()
            print('hwp thread complete')
            if need_ref:
                print('waiting for reference thread to complete')
                refthread, _ = hwp_promise
                refthread.join()
                print('reference thread complete')
            command = parse_response(
                input('[q]uit, [r]eset, or [c]ontinue (default)?: '),
                'c'
            )                
            if command == 'q':
                print('quitting')
                raise ExperimentQuit('quit command received')
            if command == 'r':                
                trial += 1
                print('retrying line measurement.')
                continue
            if command == 'c':
                breaking = True
                break
        if breaking:
            print('continuing to next line.')
            break
        print('opening molecular beam')
        init_tagging(cfg,handlerd)
        print(
            'molecular beam opened. chopper position: {:d} steps'.format(
                maxon.get_position_act(handlerd[MA])
            )
        )        
        print('getting handle to topo client')
        topoic = topo.InstructionClient()
        print('topo handle obtained.')
        print('getting handle to wavemeter')
        with wm.WavemeterHandler() as wmh:
            print('wavemeter handle obtained')
            try:
                path_creator = get_path_creator(line,cfg,sens_md,trial,handlerd)
                if gcp(cfg,'experiment','line search',bool):                    
                    searchpath = path_creator(LS,{})
                    success, result = search_line(cfg,handlerd,wmh,topoic,fo,wo,searchpath,sens_md)
                    if not success:                
                        error = result                    
                        if error == OUT_OF_RANGE_ERROR:
                            print('line search failed! continuing to next line.')
                            fp = fo
                            deltaf = gcp(cfg,'frequency scan','scan width long',float) # MHz
                        else:
                            break
                    else:
                        fp = result
                        deltaf = gcp(cfg,'frequency scan','scan width',float) # MHz
                else:
                    fp = fo
                    deltaf = gcp(cfg,'frequency scan','scan width',float) # MHz
                scanpath = path_creator(FS,{'fo':(fp,'MHz')})
                success, result = scan_frequency(cfg,handlerd,topoic,wmh,fo,wo,fp,deltaf,scanpath)                
                if not success:
                    print('frequency scan failed to find peak! continuing')
                    break
                fmax = result
                fshift = gcp(cfg,'frequency scan','off resonance shift',float)
                fmin = fmax + (
                    -1 if fmax > 0 else + 1
                ) * fshift
                fluencemd = {
                    'peak lock':{
                        key:(value,'MHz') for key, value 
                        in (('fmax',fmax),('fmin',fmin))
                    }
                }
                fluencepath = path_creator(FC,fluencemd)
                get_fluence_curve(
                    cfg,handlerd,topoic,wmh,
                    phis,fmax,fmin,fo,wo,fluencepath
                )  
                if not gcp(cfg,'experiment','angular scan',bool):
                    break
                starttime = time()
                angularmd = {
                    'start time':starttime
                }
                angularmd.update(fluencemd)
                angularpath = path_creator(AS,angularmd)
                get_angular_scan(
                    cfg,handlerd,topoic,wmh,
                    phis[0],starttime,fmax,fmin,
                    fo,wo,angularpath
                )
            except ModeHopDetected:
                print('mode hop detected!')
                print('remeasuring line')
                trial += 1
                continue
            except InterruptException:                
                print('interrupt received during measurement')
                block_molecular_beam(handlerd)
                command = parse_response(
                    input('[q]uit, [r]erun line or [c]ontinue (default)?: '),
                    'c'
                )
                if command == 'q':                        
                    raise ExperimentQuit('quit command received')
                if command == 'c':
                    break
                if command == 'r':
                    continue
            break             

def get_path_creator(line,cfg,sens_md,trial,handlerd):
    def get_path(mode,d):
        return create_dataset(
            mode,namer,line,cfg,trial,sens_md,handlerd,d
        )
    return get_path

def open_molecular_beam(handlerd):
    set_chopper_wheel(handlerd,maxon_open)

def block_molecular_beam(handlerd):
    set_chopper_wheel(handlerd,maxon_closed)

def set_chopper_wheel(handlerd,position):
    mh = handlerd[MA]
    ih = handlerd[IH]
    mode = maxon.get_operation_mode(mh)
    print('starting chopper position set to {:d} steps'.format(position))
    if mode == maxon.M_PROFILE_VELOCITY:
        print('chopper is currently spinning. initiating spin down')
        start_spin(mh,0.0)
        print('waiting for spin down')
        finish_spin(mh,ih,get_spin_cb(0))
        print('spin down complete.')
    if mode != maxon.M_PROFILE_POSITION:
        print('chopper perhaps not homed. homing')
        maxon.set_operation_mode(mh,maxon.M_HOMING)
        home_motor(mh,ih)
        print('chopper homed.')
    print('setting chopper to position mode and positioning')
    maxon.set_operation_mode(mh,M_PROFILE_POSITION)
    maxon.move_to_position(mh,position)
    print('chopper position set request complete.')

def wait_chopper(handlerd):
    maxon.wait_for_target_reached(handlerd[MA],20*1000)

def init_tagging(cfg,handlerd):
    lih = handlerd[LI]
    open_molecular_beam(handlerd)
    bolo_gain = gcp(cfg,'bolometer','gain',int) # degrees
    bologainclient.set_gain(bolo_gain)
    li_sens = gcp(cfg,'lockin','sensitivity',float)
    lockin.set_sensitivity(lih,li_sens)
    wait_chopper(handlerd)

def end_tagging(handlerd):
    lockin.set_sensitivity(handlerd[LI],1e-0)
    bologainclient.set_gain(bologainserver.X10)
    block_molecular_beam(handlerd)
    wait_chopper(handlerd)
    
def _set_hwp(cfg,handlerd,phi,lid_angle,rescon):
    res = set_hwp(cfg,handlerd,phi,lid_angle,phi)
    rescon.append(res)
def start_hwp_init(cfg,handlerd,phi):
    rescon = []
    lid_angle = gcp(cfg,'scattering','lid angle',float)
    thread = threading.Thread(
        target=_set_hwp,args=(
            cfg,handlerd,phi,lid_angle,rescon
        )
    )
    thread.start()
    return thread, rescon
def start_sensitivity(cfg,handlerd,token):
    rescon = []
    thread = threading.Thread(
        target=get_sensitivity,
        args=(cfg,handlerd,rescon,token)
    )
    thread.start()
    return thread, rescon
def end_thread(promise):
    thread, rescon = promise
    thread.join()
    return rescon.pop()

def set_line(cfg,handlerd,line):    
    dw = get_wavemeter_offset(cfg)
    ih = handlerd[IH]
    htline, piezo, e, m = line
    if e < 0 or m < 0:
        print('not initial e, m values specified.')
        emo = None
    else:
        print('eo: {:d}, mo: {:.4f}'.format(e,m))
        emo = (e,m)    
    while True:                
        success, result = tclock.locktc(htline,dw,em=emo,pv=piezo,ih=ih)
        if success:
            break
        else:
            print('tclock unsucessful!')
            print('trying again...')
    return result

def get_wavemeter_offset(cfg):
    w_ref_ref = gcp(cfg,'reference line','reference wavenumber',float) # cm-1
    w_ref_meas = gcp(cfg,'reference line','measured wavenumber',float)    
    dw = w_ref_meas - w_ref_ref
    return dw

def parse_response(response,default):
        if not response:
            return default
        else:
            return response[0].lower()

def initialize(cfg):
    # bolo gain
    bolo_gain = gcp(cfg,'bolometer','gain',int) # degrees
    bologainclient.set_gain(bolo_gain)

    # locking
    li_tau = gcp(cfg,'lockin','time constant',float)
    li_sens = gcp(cfg,'lockin','sensitivity',float)

    with lockin.LockinHandler() as lih:
        lockin.set_time_constant(lih,li_tau)
        lockin.set_sensitivity(lih,li_sens)

def get_phis(cfg):
    calib_folder = config.parse_grapher_folder(
        gcp(cfg,'fluence curve','folder')
    ) 
    calib_dsindex = gcp(cfg,'fluence curve','index',int)
    calib_fitmin = gcp(cfg,'fluence curve','min angle',float)
    calib_fitmax = gcp(cfg,'fluence curve','max angle',float)
    check_calib = gcp(cfg,'fluence curve','check calibration',bool)
    nphis = gcp(cfg,'fluence curve','angles',int)    
    calib_path = calib_folder + [gc.get_dir(calib_folder)[0][calib_dsindex]]
    irpdo, (calib_params, calib_cov) = powercalib.get_fit_params(
        calib_path,calib_fitmin,calib_fitmax
    )
    if check_calib:
        powercalib.run_demo(calib_path,calib_fitmin,calib_fitmax,nphis)
    phimax, phimin, pmax, pmin = calib_params
    phis = powercalib.get_even_powers(nphis,phimax,phimin)    
    return phis

def get_lines(cfg):
    emfile = gcp(cfg,'topo calibration','filename')
    lines = emf.parse_em_file(emfile)
    return lines

def get_initial_config():
    wsp = config.get_wavesource_params()
    lip = config.get_lockin_params()
    init_cfg_d = {
        'wavesource':wsp,
        'lockin':lip
    }
    return init_cfg_d

class ExperimentError(Exception):
    pass

class ExperimentQuit(Exception):
    pass