from transfercavity import transfercavityclient as tcc
from transfercavity import transfercavityserver as tcs
import laselock as ll
import linescan as ls
import topolock as tl
import hitran
import wavemeter as wm
from time import sleep

Nwm = 10
fitwait = 1.0

dfdw = 30.0e3 # MHz / cm-1
damping = 2.0

deltawmax = 0.05 # cm-1
epsilonw = 0.005 # cm-1

def locktc(htline,dw,em=None,ih=None):
    wtarget = hitran.lookup_line(htline)[hitran.WNUMBECK] + dw
    tcc.set_locking(False)
    tcc.set_setpoint(0.0)
    for channel in (tcs.HENE,tcs.IR):
        tcc.set_fitting(channel,False)
    tcc.set_scanning(False)
    with ll.LaseLockHandler() as llh:        
        ll.set_reg_on_off(llh,ll.A,False)
    wp, pmax, e, m = ls.set_line(htline,dw,em=em,ih=None)
    tcc.set_scanning(True)
    tl.lock_topo()
    for channel in (tcs.HENE,tcs.IR):
        tcc.set_fitting(channel,True)
    sleep(fitwait)
    tcc.zero_offset()
    tcc.set_locking(True)
    
    N = 4
    fo = 0.0
    
    with wm.WavemeterHandler() as wmh:
        while True:
            W = 0
            n = 0
            while n < N:
                W += wm.get_wavenumber(wmh)
                n += 1
            W /= N
            deltaw = W - wtarget
            print('wtarget',wtarget,'W',W,'deltaw',deltaw)
            if abs(deltaw) < epsilonw:
                break
            if abs(deltaw) > deltawmax:
                print('deltaw of {:.4f} cm-1 exceeds threshold!'.format(deltaw))
                return False, None
            fo += -dfdw*deltaw/damping
            print('wtarget',wtarget,'W',W,'deltaw',deltaw,'fo',fo)
            tcc.set_setpoint(fo)
    fp = fo
    wp = W
    return True, (e, m, fp, wp)

def unlocktc():
    pass

if __name__ == '__main__':
    import linescan as ls
    htline, dw = ls.line_wizard()
    print(locktc(htline,dw))
