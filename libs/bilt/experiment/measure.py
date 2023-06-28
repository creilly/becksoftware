from time import sleep, time
import lockin
import topo
from bilt import LI, IH, gcp, dwdf
from bilt.experiment.modehop import check_pump_wavelength
import modehop
from transfercavity import transfercavityclient as tcc

class LockinCallback:
    def __init__(self,deltat,lih,topoic):                
        self.pds = []
        self.xs = []
        self.ys = []
        self.tau_refresh = 10 * lockin.get_time_constant(lih)
        self.deltat = max(deltat,self.tau_refresh)
        self.starttime = None
        self.lih = lih        
        self.topoic = topoic

    def callback(self):
        if self.starttime is None:
            self.starttime = time()
        timep = time()        
        if timep - self.starttime >= self.tau_refresh:
            x, y = lockin.get_xy(self.lih)
            self.xs.append(x)
            self.ys.append(y)
        self.pds.append(self.topoic.get_input(topo.FAST4))                
        return timep - self.starttime < self.deltat

    def get_output(self):        
        return [
            sum(z)/len(z) for z in (self.xs,self.ys,self.pds)
        ]

def get_measurement(cfg,handlerd,topoic,wmh,wexp,deltat):
    ih = handlerd[IH]
    if ih.interrupt_received():
        ih.raise_interrupt()
    epsilonw = gcp(cfg,'mode hop','error',float) # cm-1
    lih = handlerd[LI]    
    check_pump_wavelength(cfg,handlerd)
    lockincb = LockinCallback(deltat,lih,topoic)
    success, w = modehop.monitor_mode_hop(
        wmh,
        wexp,
        epsilonw,
        lockincb.callback
    )
    if not success:
        return False, None
    x, y, pd = lockincb.get_output()
    return True, (x,y,pd,w)

## measurement subroutine
def get_dither_measurement(
    cfg,handlerd,topoic,wmh,
    deltat,fmax,fmin,fo,wo,dwdf
):
    epsilonf = gcp(cfg,'frequency scan','setpoint error',float) 
    data = []
    for f in (fmax,fmin):
        tcc.set_setpoint(f)
        tcc.check_transfer_cavity(f,epsilonf)   
        sleep(gcp(cfg,'lockin','time constant',float)*10.0)
        success, result = get_measurement(
            cfg,handlerd,topoic,wmh,                           
            wo + dwdf * (
                f - fo
            ),                            
            deltat
        )                            
        if not success:            
            return False, None
        x,y,pd,w = result
        data.extend([x,y,pd,w])
    return True, data