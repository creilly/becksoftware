from tc import tcclient as tcc
import laselock as ll
import linescan as ls
import topolock as tl
import oscilloscope, piezo, topo
import hitran
import wavemeter as wm
from beckasync import sleep, get_blocking

Nwm = 10
fitwait = 0.5
shortwait = 0.25

dfdw = 30.0e3 # MHz / cm-1
damping = 3.0

deltawmax   =   0.0500 # cm-1
epsilonw    =   0.0010 # cm-1

def disable_lock(direction):
    d = direction
    tcc.set_locking(d,False)
    tcc.set_setpoint(d,0.0,False)
    tcc.set_fitting(d,False)       

def start_lock(direction):
    d = direction
    tcc.set_fitting(d,True)
    while tcc.get_frequency(d) is None:
        yield from sleep(shortwait)    
    tcc.zero_offset(d)
    yield from sleep(shortwait)
    tcc.set_locking(d,True)

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
        htline,dw,wmh=None,opo=False,opo_entry=ls.OPO_LATEST,interrupt_handler=None
    ):
    wtarget = hitran.lookup_line(htline)[hitran.WNUMBECK] + dw
    disable_lock()
    wp, pmax, e, m = ls.set_line(
        htline,dw,wmh,opo,opo_entry,interrupt_handler
    )    
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
        htline,dw,wmh=None,opo=False,opo_entry=ls.OPO_LATEST,interrupt_handler=None
    ):
    return get_blocking(locktc_async)(htline,dw,wmh,opo,opo_entry,interrupt_handler)

def unlocktc():
    disable_lock()