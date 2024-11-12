from scipy.optimize import curve_fit
import numpy as np

# peak of amp + offset
# spacing bewteen (+ and -) peaks of 2 std
# center of symmetry at (mean,offset)
def der_gaussian(x,mean,std,amp,offset):
    return -amp * ( x - mean ) / std * np.exp(-1/2*((x-mean)/std)**2) * np.exp(1/2) + offset

def gaussian(x,mean,std,amp,offset):
    return amp * np.exp(-1/2*((x-mean)/std)**2) + offset

def gaussian_fit(xs,ys,mean,std,amp,offset):
    return curve_fit(gaussian,xs,ys,(mean,std,amp,offset))

def der_gaussian_fit(xs,ys,mean,std,amp):
    return curve_fit(der_gaussian,xs,ys,(mean,std,amp))

def fmt_gaussian(mu,sigma,amp,off):
    return ', '.join(
        '{}: {}'.format(
            label, '{:.2e}'.format(value).rjust(10)
        ) for label, value in (
            ('mu',mu), ('sigma',sigma), ('amp', amp), ('off', off)
        )
    )

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
    return xps

if __name__ == '__main__':
    from matplotlib import pyplot as plt
    xo = 1.5
    dx = 2.0
    amp = 3.0
    off = 5.0
    xs = np.linspace(xo-3*dx,xo+3*dx,100)
    noiseamp = 1.0
    ys = gaussian(xs,xo,dx,amp,off)
    zs = ys + noiseamp * (np.random.normal(0.0,noiseamp,len(xs)))
    plt.plot(xs,ys,label='exact')
    plt.plot(xs,zs,'.',label='with noise')
    guess = gaussian_guess(xs,zs)
    plt.plot(xs,gaussian(xs,*guess),label='guess')
    params, covariance = gaussian_fit(xs,zs,*guess)
    plt.plot(xs,gaussian(xs,*params),label='best fit')
    plt.xlabel('x')
    plt.ylabel('y')
    plt.title('demo of gaussian fitting')
    plt.legend()
    print('true params','\t',(xo,dx,amp,off))
    print('param guesses','\t',tuple(guess))
    print('fit params','\t',tuple(params))
    plt.show()
    
