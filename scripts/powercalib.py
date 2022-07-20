from grapher import graphclient as gc
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt

def run_demo(folder,dsindex,nphis):
    params, irpdo = get_calibration(folder,dsindex)
    phis, powers, irpds = get_dataset(folder,dsindex)
    guess = get_guess(phis,powers)
    plt.plot(phis,powers,'.',label='calib data')
    for ps, label in ((guess,'guess'),(params,'fit')):
        plt.plot(phis,get_calibration_function(ps)(phis),label=label)
    phips = get_even_powers(params,nphis)
    first = True
    for phi in phips:
        plt.plot(
            [0,phi],
            [sine_curve(phi,*params)]*2,
            color='black',
            **(
                {
                    'label':'fc points'
                } if first else {}
            )   
        )
        first = False
        plt.plot([phi]*2,[sine_curve(phi,*params),0],color='black')
    plt.xlabel('hwp angle (degrees)')
    plt.ylabel('power (watts)')
    plt.title('power calibration')
    plt.legend()
    plt.show()

def get_guess(phis,powers):
    nmax = powers.argmax()
    nmin = powers.argmin()
    phio = phis[nmax]
    deltaphi = 2*abs(phis[nmin]-phio)
    while phio > 0:
        phio -= deltaphi
    phio += deltaphi
    pmin = powers[nmin]
    pmax = powers[nmax]
    
    guess = (phio,deltaphi,pmin,pmax)

    return guess

def get_dataset(folder,dsindex):
    return gc.get_data_np(
       folder + [gc.get_dir(folder)[0][dsindex]]
    )

def sine_curve(phi,phio,deltaphi,pmin,pmax):
    return pmin + 1 / 2 * (pmax - pmin) * (
        1 + np.cos(
            2 * np.pi * (phi - phio) / deltaphi
        )
    )

def get_calibration_function(params):
    return lambda phi: sine_curve(phi,*params)

def get_even_powers(params,nphis):
    phio,deltaphi,pmin,pmax = params
    return phio + deltaphi / (2 * np.pi) * np.arccos(np.linspace(1,-1,nphis))

def get_calibration(folder,dsindex):
    phis, powers, irpds = get_dataset(folder,dsindex)
        
    guess = get_guess(phis,powers)

    params, cov = curve_fit(sine_curve,phis,powers,guess)

    return params, np.average(irpds)

if __name__ == '__main__':
    import argparse

    nphis = 20

    parser = argparse.ArgumentParser(
        description="module for working with power calibrations"
    )
    parser.add_argument(
        'folder',
        nargs='*',
        help='the grapher folder where the calibration data is stored.' \
            ' e.g., <2022 03 15 "power calibration"> (without < or >)'
    )
    parser.add_argument(
        'dsindex',
        type=int,
        help='index of dataset containing calibration data'
    )
    args = parser.parse_args()
    folder = args.folder
    dsindex = args.dsindex
    
    run_demo(folder,dsindex,nphis)