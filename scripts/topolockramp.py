import topo
import numpy as np
import piezo
import laselock as ll
import oscilloscope as scope

DELTAVS = (2.0,1.0,0.6,0.25,0.10)
DVS = (100e-5,50e-5,25e-5,10e-5,1e-5)
POS, NEG = 'p', 'n'
POLS = (POS,NEG)

PVo = 20.0 # volts piezo output

dither_amp = 6.7000 # volts # from 2022-11-18 calibration

noise_amp = 0.140 # volts rms
ws_shape = scope.NOISE
ws_enabled = True
ws_load = scope.LOW

Vo = 2.0 # volts piezo input

dVdt = 2.0 # volts per second

def setup_lock(
        sh : scope.ScopeHandler,        
        llh : ll.LaseLockHandler
    ):    
    scope.set_wavesource_enabled(sh,ws_enabled)
    scope.set_wavesource_shape(sh,ws_shape)
    scope.set_output_impedance(sh,ws_load)
    scope.set_rms_noise(sh,noise_amp)    

    ll.set_reg_on_off(llh,ll.A,False)    
    ll.set_li_ampl_aux(llh,0.0)    

dpvdv = 75 / 10

def lock_topo_async(
        ic : topo.InstructionClient,
        sh : scope.ScopeHandler,
        pdh : piezo.PiezoDriverHandler,
        llh : ll.LaseLockHandler,
        pol = POS
    ):    
    ic.set_wide_scan_input(topo.INPUT1,topo.FINE1)
    ic.set_wide_scan_input(topo.INPUT2,topo.NOINPUT)
    ic.set_wide_scan_speed(dVdt)
    setup_lock(sh,llh)    
    pv = PVo
    piezo.set_piezo_voltage(pdh,pv)    
    vo = None
    for dv, deltav in zip(DVS, DELTAVS):        
        if vo is not None:   
            pv = update_piezo(pdh,pv,vo)
        vo = yield from find_peak(ic,Vo,deltav,dv,pol)
        print(
            ', '.join(
                '{}: {} {}'.format(
                    label, 
                    '{{:.{:d}f}}'.format(precision).format(value), 
                    unit
                ) for label, value, precision, unit in (
                    ('dv',  deltav, 2,  'v in'  ),
                    ('vo',  vo,     3,  'v in'  ),
                    ('pv',  pv,     2,  'v out' )
                )
            )
        )        
    ic.set_output(topo.A,vo)
    finish_lock(ic,llh)

def lock_topo(
        ic : topo.InstructionClient,
        sh : scope.ScopeHandler,
        pdh : piezo.PiezoDriverHandler,
        llh : ll.LaseLockHandler,
        pol = POS
    ):        
        for _ in lock_topo_async(ic,sh,pdh,llh,pol): pass            

def update_piezo(pdh : piezo.PiezoDriverHandler, pzvout : float, pzvin : float):
    pv = pzvout
    vo = pzvin
    dvo = vo - Vo
    dpv = dpvdv * dvo 
    pvp = pv + dpv               
    piezo.set_piezo_voltage(pdh,pvp)
    return pvp
    
def finish_lock(ic : topo.InstructionClient, llh : ll.LaseLockHandler):
    set_dither(llh, True)    
    ll.set_reg_on_off(llh,ll.A,True)

def set_dither(llh : ll.LaseLockHandler, dithering : bool):
    ll.set_li_ampl_aux(
        llh,{
            True:dither_amp, False:0.0
        }[dithering]
    )

def find_peak(
        ic : topo.InstructionClient, 
        vo : float, deltav : float, dv : float, 
        pol = POS
    ):    
    ic.set_wide_scan_begin(vo-deltav/2)
    ic.set_wide_scan_end(vo+deltav/2)
    ic.set_wide_scan_step(dv)
    wide_scan = yield from topo.get_wide_scan_async(ic)
    xdata, ydata, *_ = map(np.array,wide_scan)
    if pol == NEG:        
        ydata *= -1
    nmax = ydata.argmax()
    xmax, ymax = xdata[nmax], ydata[nmax]    
    vo = xmax
    return vo
        
if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='locks topo to fabry perot')
    ap.add_argument('-p','--polarity',choices=POLS,default=POS,help='is signal [p]ositive or [n]egative going')
    pol = ap.parse_args().polarity
    with (
        scope.ScopeHandler() as sh,
        piezo.PiezoDriverHandler() as pdh,
        ll.LaseLockHandler() as llh
    ):
        ic = topo.InstructionClient()
        lock_topo(ic,sh,pdh,llh,pol)
