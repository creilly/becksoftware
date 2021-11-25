from scipy.optimize import curve_fit
import numpy as np

def der_gaussian(x,mean,std,amp):
    return -amp * ( x - mean ) * np.exp(-1/2*((x-mean)/std)**2)

def gaussian(x,mean,std,amp,offset):
    return amp * np.exp(-1/2*((x-mean)/std)**2) + offset

def gaussian_fit(xs,ys,mean,std,amp,offset):
    return curve_fit(gaussian,xs,ys,(mean,std,amp,offset))

def der_gaussian_fit(xs,ys,mean,std,amp):
    return curve_fit(der_gaussian,xs,ys,(mean,std,amp))

MEAN, STD, AMP, OFFSET = 0, 1, 2, 3
def gaussian_guess(xs,ys):
    offset = ys.min()
    zs = ys - offset
    mean = sum(xs*zs)/sum(zs)    
    std = np.sqrt(sum(xs**2*zs)/sum(zs) - mean**2)
    amp = zs.max()
    return (mean,std,amp,offset)

# dphi: accuracy in radians
def auto_phase(xs,ys,dphi):
    phases = np.arange(0,2*np.pi,dphi)
    return phases[
        np.sum(
            (
                np.outer(xs,np.sin(phases)) -
                np.outer(ys,np.cos(phases))
            )**2,
            0
        ).argmin()
    ]

def rephase(xs,ys,phase):
    return xs * np.cos(phase) + ys * np.sin(phase)
    
def decimate(xs,N):
    xps = []
    xp = xs[0]
    for n,x in enumerate(xs):
        xp = (N-1)/N*xp + 1/N*x
        if n % N >= N - 1:
            xps.append(xp)
    return np.array(xps)
