from matplotlib import pyplot as plt
import numpy as np
import argparse
from beckfile import get_fname

infilesarg = 'input .dat files'
ap = argparse.ArgumentParser()
ap.add_argument(infilesarg,nargs='+')
ap.add_argument('-m','--min',type=float,default=-1.0,help='min energy to start min/max scaling')
args = ap.parse_args()
infilenames = vars(args)[infilesarg]
minenergy = args.min

froot = input('enter image filename (no ext): ')
desc = input('enter description: ')

skiprows = 24
n = 0
while infilenames:
    label = infilenames.pop()
    fname = infilenames.pop()
    n += 1

    e, s = np.loadtxt(fname,skiprows=skiprows).transpose()

    minindex = 0
    if min > 0:
        for index in range(len(e)):
            if e[index] > min:
                break
            minindex = index

    s /= s[minindex:].max() - s[minindex:].min()

    s -= np.average(s)

    e /= 1e3

    plt.plot(e,s,':',label=label,lw=1)
plt.xlabel('auger electron energy (eV)')
plt.ylabel('auger signal (normalized)')
plt.title('auger electron spectrum' + '\n' + desc)
if n > 1:
    plt.legend()
plt.savefig(get_fname(desc,'png'))
plt.show()