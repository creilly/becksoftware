from transfercavity import transfercavityclient as tcc
from transfercavity import transfercavityserver as tcs
import laselock as ll
import linescan as ls
import topolock as tl
import oscilloscope, piezo, topo
import hitran
import wavemeter as wm
from beckasync import sleep, get_blocking

Nwm = 10
fitwait = 1.0

dfdw = 30.0e3 # MHz / cm-1
damping = 3.0

deltawmax   =   0.0500 # cm-1
epsilonw    =   0.0010 # cm-1

def disable_lock():
    tcc.set_locking(False)
    tcc.set_setpoint(0.0)
    for channel in (tcs.HENE,tcs.IR):
        tcc.set_fitting(channel,False)
    tcc.set_scanning(False)
    with ll.LaseLockHandler() as llh:        
        ll.set_reg_on_off(llh,ll.A,False)

def setup_lock():
    tcc.set_scanning(True)

def start_lock():    
    for channel in (tcs.HENE,tcs.IR):
        tcc.set_fitting(channel,True)
    yield from sleep(fitwait)
    tcc.zero_offset()
    tcc.set_locking(True)

def finish_lock(wmh,wtarget):
    N = 4
    fo = 0.0
    while True:
        W = 0
        n = 0
        while n < N:
            W += yield from wm.get_wavenumber_async(wmh)
            n += 1
        W /= N
        deltaw = W - wtarget
        print(
            ', '.join(
                '{}: {} {}'.format(
                    label, 
                    '{{:.{:d}f}}'.format(precision).format(value), 
                    unit
                ) for label, value, precision, unit in (
                    ('wo',  wtarget,    4,  'cm-1'  ),
                    ('w',   W,          4,  'cm-1'  ),
                    ('dw',  deltaw,     4,  'cm-1'  ),
                    ('fo',  fo,         1,  'mhz'   )       
                )            
            )
        )
        if abs(deltaw) < epsilonw:
            break
        if abs(deltaw) > deltawmax:
            print('dw of {:.4f} cm-1 exceeds threshold!'.format(deltaw))
            return False, None
        fo += -dfdw*deltaw/damping        
        tcc.set_setpoint(fo)
    fp = fo
    wp = W
    return True, (fp, wp)

def locktc_async(
        htline,dw,
        em=None,pv=None,ih=None,dt=None,
        opo=False
    ):
    wtarget = hitran.lookup_line(htline)[hitran.WNUMBECK] + dw
    disable_lock()
    wp, pmax, e, m = ls.set_line(
        htline,dw,em=em,pv=pv,ih=ih,opo=opo,dt=dt
    )
    setup_lock()
    with (
        oscilloscope.ScopeHandler() as sh,
        piezo.PiezoDriverHandler() as pdh,
        ll.LaseLockHandler() as llh
    ):
        yield from tl.lock_topo_async(topo.InstructionClient(),sh,pdh,llh,tl.POS)
    yield from start_lock()
    with wm.WavemeterHandler() as wmh:
        success, result = yield from finish_lock(wmh,wtarget)
        if success:
            f, w = result
        else:
            return False, None
    return True, (e, m, f, w)

def locktc(
        htline,dw,
        em=None,pv=None,ih=None,dt=None,
        opo=False
    ):
    return get_blocking(locktc_async)(htline,dw,em,pv,ih,dt,opo)

def unlocktc():
    disable_lock()

if __name__ == '__main__':
    import linescan as ls
    import argparse
    ap = argparse.ArgumentParser(description='sets topo to desired line and locks to transfer cavity')
    ap.add_argument('-e','--etalon',type=int,help='etalon position (must be integer)')
    ap.add_argument('-m','--motor',type=float,help='motor position (float, in mm)')
    args = ap.parse_args()
    em = args.etalon, args.motor
    if None in em:
        em = None    
    htline, dw = ls.line_wizard()
    print(locktc(htline,dw,em=em))
