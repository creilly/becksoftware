from sympy import Mod
from bilt.experiment.modehop import ModeHopDetected
from bilt.experiment.hwp import set_hwp
from bilt.experiment.measure import get_dither_measurement
from bilt import gcp, dwdf
from grapher import graphclient as gc

def get_fluence_curve(cfg,handlerd,topoic,wmh,phis,fmax,fmin,fo,wo,path):
    lid_angle = gcp(cfg,'scattering','lid angle',float)   
    deltat_fc = gcp(cfg,'fluence curve','measure time',float) 
    for phi in phis:
        data = []
        data.append(phi)                    
        deltax, deltay = set_hwp(cfg,handlerd,phi,lid_angle)
        success, outdata = get_dither_measurement(
            cfg,handlerd,topoic,wmh,
            deltat_fc,fmax,fmin,fo,wo,dwdf
        )
        if not success:
            raise ModeHopDetected()
        data.extend(outdata)
        data.extend([deltax,deltay])
        gc.add_data(path,data)