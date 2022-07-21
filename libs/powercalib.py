from scipy.optimize import curve_fit
from grapher import graphclient as gc
import numpy as np
from matplotlib import pyplot as plt

def hwpfit(phi,phimax,phimin,pmax,pmin):
    amplitude = 1/2 * (pmax - pmin)
    offset = pmin + amplitude
    return offset + amplitude * np.cos(
        2 * np.pi * (phi - phimax) / (2 * (phimax-phimin))
    )

def get_even_powers(nphis,phimax,phimin):
    return phimax + (phimin-phimax) / np.pi * np.arccos(
        np.linspace(1,-1,nphis)
    )

def get_fit_params(path,phimin,phimax):
    phis, powers, irpds = gc.get_data_np(path)

    irpdo = np.average(irpds)

    fitphis, fitpowers = map(
        np.array,
        zip(
            *[
                (phi, power) for phi, power in zip(phis,powers)
                if phi > phimin and phi < phimax
            ]
        )
    )

    phimaxo = fitphis[fitpowers.argmax()]
    phimino = fitphis[fitpowers.argmin()]    
    pmaxo = fitpowers.max()
    pmino = fitpowers.min()    

    guess = (phimaxo,phimino,pmaxo,pmino)

    ps, cov = curve_fit(hwpfit,fitphis,fitpowers,guess)

    return irpdo, (ps,cov)

def get_power_calib(irpdo,params):
    def power(phi,irpd):
        return irpd / irpdo * hwpfit(phi,*params)
    return power

def run_demo(path,phimin,phimax,nphis):
    irpdo, (params,cov) = get_fit_params(path,phimin,phimax)
    pcalib = get_power_calib(irpdo,params)    
    phis, powers, irpds = gc.get_data_np(path)
    plt.plot(phis,powers,'.',label='data')
    plt.plot(phis,pcalib(phis,irpdo),label='fit')
    phimax, phimin, pmax, pmin = params
    phips = get_even_powers(nphis,phimax,phimin)
    first = True
    powerprev = None
    deltapowers = []
    for phi in phips:
        power = pcalib(phi,irpdo)
        plt.plot(
            [0,phi],
            [power]*2,
            color='black',
            **(
                {
                    'label':'fc points'
                } if first else {}
            )   
        )
        if powerprev is not None:
            deltapowers.append(power-powerprev)
        powerprev = power
        first = False
        plt.plot([phi]*2,[pcalib(phi,irpdo),0],color='black')    
    plt.xlabel('hwp angle (degrees)')
    plt.ylabel('power (watts)')
    plt.title(
        'power calibration - {}'.format(
            r'${} = {} \times 10^{{{}}}$ watts'.format(
                r'\sigma_{\Delta P}',
                *'{:.2e}'.format(np.std(deltapowers)).split('e')
            )
        )
    )
    plt.legend()
    plt.show()

if __name__ == '__main__':    
    folder = ['2022','05','25']
    ds = 1

    phimin = 5.0 # degrees
    phimax = 52.0

    path = folder + [gc.get_dir(folder)[0][ds]]

    nphis = 10

    run_demo(path,phimin,phimax,nphis)