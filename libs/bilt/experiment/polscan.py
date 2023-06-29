from bilt.experiment.modehop import ModeHopDetected
from transfercavity import transfercavityclient as tcc
from bologain import bologainclient
from bilt import gcp, LI, dwdf, RST, RS
import numpy as np
from time import time
import lockin, rotationstage as rs
from bilt.experiment.measure import get_measurement
from grapher import graphclient as gc

def get_polarization_scan(
    cfg,handlerd,topoic,wmh,fmax,fmin,wo,path
):
    tag_hwp = gcp(cfg,'fluence curve','calib angle',float)
    rs.set_angle(handlerd[RS],tag_hwp)

    deltat_measure = gcp(cfg,'pol scan','measure time',float)
    deltat_bg = gcp(cfg,'pol scan','background time',float)

    scan_start = gcp(cfg,'pol scan','scan start',float)
    scan_stop = gcp(cfg,'pol scan','scan stop',float)
    scan_step = gcp(cfg,'pol scan','scan step',float)

    reference_angle = gcp(cfg,'pol scan','reference angle',float)

    phis = np.arange(scan_start,scan_stop,scan_step)    

    print('getting background')
    tcc.set_setpoint(fmin)
    success, result = get_measurement(cfg,handlerd,topoic,wmh,wo,deltat_bg)
    if not success:
        raise ModeHopDetected()
    tcc.set_setpoint(fmax)
    xo, yo, pd, w = result
    print('background level:','{:.1f} microvolts'.format(1e6*xo))
    bgd = {
        'photodiode':(pd,'volts'),
        'lockin':(
            {
                'x':xo,
                'y':yo
            },'volts'
        ),
        'wavemeter':(w,'cm-1')
    }
    *dspbase, dsptail = path
    mdptail = dsptail[:-3] + 'bmd'
    mdp = [*dspbase,mdptail]
    gc.update_metadata(mdp,bgd)

    for phi in phis:
        rs.set_angle(handlerd[RST],phi)
        data = [] 
        data.append(phi)  
        success, result = get_measurement(cfg,handlerd,topoic,wmh,wo,deltat_measure)
        if not success:
            raise ModeHopDetected()      
        x, y, pd, w = result        
        data.extend(
            [
                x-xo,y-yo,pd,w
            ]
        )        
        gc.add_data(path,data)  
    rs.set_angle(
        handlerd[RST],
        reference_angle
    )  