from bilt import gcp, dwdf, IH
import numpy as np
from transfercavity import transfercavityclient as tcc
from bilt.experiment.measure import get_measurement
from grapher import graphclient as gc
from scipy.optimize import curve_fit
from bilt.experiment.modehop import ModeHopDetected

def format_step(f,x,y,pd,w):
    return ' '.join(
        [
            'scan:',
            ', '.join(
                [
                        '\t:\t'.join(
                        [
                            label,
                            ' '.join(
                                [                                    
                                    fmt.format(val).rjust(width),
                                    unit,
                                ]
                            )
                        ]
                    ) for label, fmt, val, width, unit in 
                    (
                        ('f','{:.2f}',f,8,'MHz'),
                        ('x','{: 5d}',int(1e6*x),7,'uv'),
                        ('y','{: 5d}',int(1e6*y),7,'uv'),
                        ('p','{: 3d}',int(1e3*pd),4,'mv'),
                        ('w','{:.4f}',w,10,'cm-1'),
                    )
                ]
            )
        ]
    )

def scan_frequency(cfg,handlerd,topoic,wmh,fo,wo,fc,path):
    deltaf = gcp(cfg,'frequency scan','scan width',float) # MHz
    df = gcp(cfg,'frequency scan','scan increment',float)
    deltat_tc = gcp(cfg,'frequency scan','measure time',float)
    epsilonf = gcp(cfg,'frequency scan','setpoint error',float)
    
    fs = np.arange(fc-deltaf/2,fc+deltaf/2,df)
    xs = []
    pds = []
    for f in fs:
        tcc.set_setpoint(f)
        tcc.check_transfer_cavity(f,epsilonf)                
        success, result = get_measurement(
            cfg,handlerd,topoic,wmh,wo + dwdf * ( f - fo ),deltat_tc
        )        
        if not success:
            raise ModeHopDetected()
        x,y,pd,w = result
        xs.append(x)
        pds.append(pd)
        gc.add_data(
            path,
            (f,x,y,pd,w)
        )        
        print(format_step(f,x,y,pd,w))
    xs = np.array(xs)
    pds = np.array(pds)    
    def fit(x,mean,std,amp,offset):
        return amp * np.exp(
            -1/2*(
                (fs-mean)/std
            )**2
        ) + offset * pds/np.average(pds)
    guess = (
        fs[xs.argmax()],9.0,xs.max()-np.average(xs),np.average(xs)
    )
    try:
        params, cov = curve_fit(fit,fs,xs,guess)                
    except Exception:
        return False, None
    print(
        'params',
        ', '.join(
            [
                '{} : {} {}'.format(
                    label,'{:.2e}'.format(val).rjust(10),unit
                ) for label, val, unit in zip(
                    ('mu','sigma','amp','offset'),
                    params,
                    ('MHz','MHz','volts','volts')
                )
            ]
        )
    )
    fmax = params[0]
    return True, fmax