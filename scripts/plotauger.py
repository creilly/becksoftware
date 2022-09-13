from matplotlib import pyplot as plt
import numpy as np
import argparse
from beckfile import get_fname

infilearg = 'input .dat file'
ap = argparse.ArgumentParser()
ap.add_argument(infilearg)
infilename = vars(ap.parse_args())[infilearg]

froot = input('enter image filename (no ext): ')
desc = input('enter description: ')

skiprows = 24

e, s = np.loadtxt(infilename,skiprows=skiprows).transpose()

s /= s.max() - s.min()

s -= np.average(s)

e /= 1e3

plt.plot(e,s)
plt.xlabel('auger electron energy (eV)')
plt.ylabel('auger signal (normalized)')
plt.title('auger electron spectrum' + '\n' + desc)
plt.savefig(get_fname(desc,'png'))
plt.show()