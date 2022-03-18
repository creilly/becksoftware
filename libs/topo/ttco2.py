import os
import numpy as np
folder = r'Z:\Surface\chris\calibrations\topo\co2'
efile = 'etalon.txt'
mfile = 'motor.txt'

def load_params(fname):
    with open(os.path.join(folder,fname),'r') as f:
        return list(
            map(float,f.read().strip().split('\n')[-1].split('\t'))
        )

def load_etalon_params():
    return load_params(efile)

def load_motor_params():
    return load_params(mfile)

eparams = load_etalon_params()
mparams = load_motor_params()

emin = 5850
emax = 6500
mmin = -2
mmax = 9
def get_etalon(w):
    m = mmin
    wmin = w_from_e(emin,m,*eparams)
    if w < wmin:
        raise Exception('w too low!')
    while True:
        if m > mmax:
            raise Exception('w too high!')
        wmax = w_from_e(emax,m,*eparams)
        if wmax > w:
            wbar, wo, eo, b = eparams            
            e = eo - 1 / b * np.sqrt(
                2 * ( 1 - w / (wbar + m * wo) )
            )
            dedw = 1/b * 1/(wbar + m * wo) / np.sqrt(
                2 * ( 1 - w / (wbar + m * wo) )
            )
            eint = e - dedw * w
            return (e,dedw)
        m += 1

def get_motor(w):
    m, b = mparams
    return (m*w + b,m)

def w_from_e(e,m,wbar,wo,eo,b):
    return (wbar + m*wo)*(
        1 - 1/2*(
            b*(e-eo)
        )**2
    )

if __name__ == '__main__':
    print(get_etalon(3640))
    print(get_motor(3700))
