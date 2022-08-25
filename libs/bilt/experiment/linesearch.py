from transfercavity import transfercavityclient as tcc
from grapher import graphclient as gc
from bilt import gcp, dwdf
from bilt.experiment import measure
from bilt.experiment.modehop import ModeHopDetected
import numpy as np

def search_line(cfg,handlerd,wmh,topoic,fo,wo,path,sens_md):
    sens_scalar = sens_md['measurement']['r'][0]
    deltaf = gcp(cfg,'line search','jump size',float)
    deltat = gcp(cfg,'line search','measure time',float)
    deltaxthresh = gcp(cfg,'line search','step threshold',float)

    data = {}    
    index = 0

    ABOVE, BELOW = 0, 1    

    searcher = Searcher(
        cfg,handlerd,wmh,topoic,
        deltat,fo,wo,deltaf,data,path
    )
    try:
        print('starting gradient detection')
        while True:
            jumpindex = jumper(index)
            searcher.get_measurement(jumpindex)        
            if not index:
                index += 1    
                continue
            jumpindexprev = jumpindex + {
                True:-1,
                False:+1
            }[jumpindex > 0]
            deltax = data[jumpindex] - data[jumpindexprev]
            if abs(deltax) / sens_scalar > deltaxthresh:            
                break
            index += 1    
        print('gradient detected.')
        if deltax > 0:
            xthresh = data[jumpindex]
            step = +1 if jumpindex > 0 else -1        
        else:
            xthresh = data[jumpindexprev]
            step = -1 if jumpindex > 0 else +1    
        jumpindex += step
        print('starting threshold crossing detection')    
        while True:
            if jumpindex not in data:
                searcher.get_measurement(jumpindex)
            if data[jumpindex] < xthresh:
                break
            jumpindex += step
        print('threshold crossing detection complete.')
        maxindex = max(data.items(),key=lambda x: x[1])[0]
        fp = fo + deltaf * maxindex
        print(
            'search index of max signal: {:d}, max tc freq: {:.1f} MHz'.format(
                maxindex,fp
            )
        )
        return True, fp
    except OutOfRange:
        # todo! implement curve fitting extra protection
        # return True, 0.0
        return False, OUT_OF_RANGE_ERROR    

MODE_HOP_ERROR, OUT_OF_RANGE_ERROR = 0, 1

def jumper(n):
    N = (n+1) // 2    
    sign = (-1) ** ( N + n )        
    return sign * N

class Searcher:
    def __init__(
        self,cfg,handlerd,
        wmh,topoic,deltat,
        fo,wo,deltaf,data,
        path
    ):        
        self.dfmax = gcp(cfg,'line search','search range',float)
        self.epsilonf = gcp(cfg,'frequency scan','setpoint error',float)
        self.cfg = cfg
        self.handlerd = handlerd
        self.wmh = wmh
        self.topoic = topoic
        self.deltat = deltat                
        self.fo = fo
        self.wo = wo        
        self.deltaf = deltaf
        self.data = data        
        self.path = path

    def get_measurement(self,jump_index):
        df = self.deltaf * jump_index
        if abs(df) > self.dfmax:
            print(
                'no gradient found within {:.1f} MHz of start!'.format(
                    self.dfmax
                )
            )        
            raise OutOfRange()
        dw = dwdf * df
        w = self.wo + dw
        f = self.fo + df
        tcc.set_setpoint(f)
        tcc.check_transfer_cavity(f,self.epsilonf)
        success, result = measure.get_measurement(
            self.cfg,
            self.handlerd,
            self.topoic,
            self.wmh,
            w,
            self.deltat
        )
        if success:
            x, y, pd, w = result
            print(format_step(df,x))
            self.data[jump_index] = x            
            gc.add_data(self.path,[f,*result])
        else:
            raise ModeHopDetected()

class OutOfRange(Exception):
    pass

def format_step(df,x):
    return ', '.join(
        (
            'search df:','{:.1f}'.format(df).rjust(10),'MHz',
            '|',
            'x:', '{:.1f}'.format(1e6*x).rjust(20),'microvolts'
        )
    )