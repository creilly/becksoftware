from scipy.optimize import curve_fit
from grapher import graphclient as gc
import numpy as np

mirrorloss = 0.1

def hwpfit(phi,phimax,phimin,pmax,pmin):
    amplitude = 1/2 * (pmax - pmin)
    offset = pmin + amplitude
    return offset + amplitude * np.cos(
        2 * np.pi * (phi - phimax) / (2 * (phimax-phimin))
    )

def get_power_calib(path,phimin,phimax):    
    phis, powers, irpds = gc.get_data_np(path)
    powers *= (1-mirrorloss)
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

    ps, covs = curve_fit(hwpfit,fitphis,fitpowers,guess)

    def power(phi,irpd):
        return irpd / irpdo * hwpfit(phi,*ps)

    return power

if __name__ == '__main__':
    from grapher import graphclient as gc
    from matplotlib import pyplot as plt

    folder = ['2022','05','25']
    ds = 1

    phimin = 5.0 # degrees
    phimax = 52.0

    path = folder + [gc.get_dir(folder)[0][ds]]

    phis, ps, irpds = gc.get_data_np(path)

    plt.plot(phis,(1-mirrorloss)*ps,'.',label='data')

    power = get_power_calib(path,phimin,phimax)

    plt.plot(phis,power(phis,np.average(irpds)),label='fit')

    plt.legend()
    plt.xlabel('hwp angle (degs)')
    plt.ylabel('transmission-corrected power (watts)')
    plt.title('power calibration')
    plt.show()