from sympy.physics.quantum.cg import CG # (j1, m1, j2, m2, j3, m3)
import sympy
import json
import numpy as np
from matplotlib import pyplot as plt

epsilon_o = 8.85e-12 # farads / m
c = 3.0e8 # m / s
h = 6.63e-34 # m2 kg / s

# SI units
def elec_field(intensity):
    return np.sqrt(
        2 * intensity / (
            c * epsilon_o
        )
    )

# cm-1 to rad/s
def radial_frequency(wavenumber):
    w_cm = wavenumber
    w_m = w_cm * 1e2
    lambda_m = 1/w_m    
    freq = c / lambda_m
    omega = 2*np.pi * freq
    return omega

# dipole moment (SI units)
def mu(lj,uj,m,w,a):
    cgc_sym = CG(
        lj,m,1,0,uj,m
    )
    cgc = float(np.abs(sympy.N(cgc_sym.doit())))    
    if cgc == 0.0:
        return 0.0
    return cgc * np.sqrt(
        3 * epsilon_o * h * c**3 / (
            2 * radial_frequency(w)**3
        ) * a
    )

# Hz
def rabi_freq(lj,uj,m,w,a,i):
    return mu(lj,uj,m,w,a) * elec_field(i) / h

# rad / s
def rabi_rad_freq(lj,uj,m,w,a,i):
    return rabi_freq(lj,uj,m,w,a,i) * 2 * np.pi

if __name__ == '__main__':
    import hitran
    linesfile = 'eins_new.json'
    power = 1 # watt
    radius = 2e-3 # meters

    linesd = json.load(open(linesfile,'r'))

    rabi_freqs = []
    i = power/(np.pi*radius**2)
    for line, folders in linesd.items():        
        lined = hitran.lookup_line(folders)
        w = lined[hitran.WNUM]
        a = lined[hitran.EIN_COEFF]
        *rootfolders, llq, ulq = folders
        lj, lsym, ll = hitran.parse_lq(llq)
        uj, usym, ul = hitran.parse_lq(ulq)        
        j = min(lj,uj)
        for m in np.arange(2*j+1) - j:
            rabi_freqs.append(
                rabi_freq(
                    lj,uj,m,w,a,i
                ) * 2 * radius / 1000.0
            )
    plt.xlabel('rabi cycles')
    plt.ylabel('occurences')
    plt.title('rabi cycles distribution for test set')
    plt.hist(rabi_freqs)
    # plt.savefig(get_fname('rabi-cycles','png'))
    plt.show()