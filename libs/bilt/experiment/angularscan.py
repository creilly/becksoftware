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

def get_angular_scan(
    cfg,handlerd,topoic,wmh,
    phio,starttime,fmax,fmin,fo,wo,path
):
    deltat_as = gcp(cfg,'angular scan','measure time',float)

    thetas = get_thetas(cfg)

    lih = handlerd[LI]
    li_sens = gcp(cfg,'lockin','sensitivity',float)

    bolo_gain = gcp(cfg,'bolometer','gain',int) # degrees
    for theta in thetas:
        bologainclient.set_gain(bologainserver.X10)
        lockin.set_sensitivity(lih,1e-0)
        lidclient.set_lid(theta)
        deltax, deltay = set_hwp(cfg,handlerd,phio,theta,phio)
        lidclient.wait_lid(
            lambda: print(
                'waiting for lid. requested: {:.2f} degs, actual: {:.2f} degs'.format(
                    theta,lidclient.get_lid()
                )
            )
        )
        print('angle:',int(1000*theta),'milldegrees')                    
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