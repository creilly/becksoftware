from bilt.experiment.modehop import ModeHopDetected
from bologain import bologainclient, bologainserver
from bilt import gcp, LI, dwdf
import numpy as np
from time import time
import lockin
from lid import lidclient
from bilt.experiment.hwp import set_hwp
from bilt.experiment.measure import get_dither_measurement
from grapher import graphclient as gc

def lidcallback(thetap):
    delay = 5.0 # seconds
    timer = [time()]
    def cb():
        tp = time()
        to = timer[0]
        if tp - to > delay:
            print(
                'waiting for lid. requested: {:.2f} degs, actual: {:.2f} degs'.format(
                    thetap,lidclient.get_lid()
                )
            )
            timer[0] = tp
    return cb

def get_angular_scan(
    cfg,handlerd,topoic,wmh,
    phio,starttime,fmax,fmin,fo,wo,path
):
    deltat_as = gcp(cfg,'angular scan','measure time',float)

    thetas = get_thetas(cfg)

    lih = handlerd[LI]
    li_sens = gcp(cfg,'lockin','sensitivity',float)

    bolo_gain = gcp(cfg,'bolometer','gain',int) # degrees

    lockin.clear_status_registers(lih)
    for theta in thetas:
        bologainclient.set_gain(bologainserver.X10)
        lockin.set_sensitivity(lih,1e-0)
        lidclient.set_lid(theta,wait=False)
        encoder = lidclient.get_encoder()
        deltax, deltay = set_hwp(cfg,handlerd,phio,theta)
        lidclient.wait_lid(lidcallback(theta))                    
        data = [] 
        data.append(theta)
        lockin.set_sensitivity(lih,li_sens)
        bologainclient.set_gain(bolo_gain)                  
        while lockin.get_overloaded(lih):
            print('lockin overloaded!')
            continue                    
        success, outdata = get_dither_measurement(
            cfg,handlerd,topoic,wmh,
            deltat_as,fmax,fmin,fo,wo,
            dwdf
        )
        if not success:
            raise ModeHopDetected()
        data.extend(outdata)
        data.extend([deltax,deltay])
        data.append(time() - starttime)
        data.append(encoder)
        gc.add_data(path,data)    

def get_thetas(cfg):
    lid_angle = gcp(cfg,'scattering','lid angle',float)
    theta_center = gcp(cfg,'angular scan','scan center',float)
    delta_theta = gcp(cfg,'angular scan','scan width',float)
    dtheta = gcp(cfg,'angular scan','scan increment',float)

    thetas_head = np.arange(
        lid_angle,
        theta_center + delta_theta / 2 + dtheta / 2,
        dtheta
    )

    thetas_tail = np.arange(
        theta_center - delta_theta / 2,
        lid_angle,    
        dtheta
    )

    thetas = np.hstack(
        [
            thetas_head,
            thetas_tail,
            [lid_angle-0.0001]
        ]
    )    
    return thetas