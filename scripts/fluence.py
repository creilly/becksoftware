from grapher import graphclient as gc
from matplotlib import pyplot as plt
import fit
import numpy as np
from scipy.optimize.optimize import OptimizeWarning
import warnings
import os
import matplotlib as mpl

warnings.filterwarnings('error')

saveroot = r'Z:\Surface\chris\scripts-data'

def get_folder(prompt,folder = []):
    while True:
        print('current folder:','\t:\t'.join(folder))
        folders = gc.get_dir(folder)[1]
        print(
            '\n'.join(
                '{:d}\t:\t{}'.format(
                    index,folder
                ) for index, folder in enumerate(
                    ['select folder','go back'] + folders
                )
            )
        )
        folderindex = input('{}: '.format(prompt))
        if not folderindex:
            folderindex = len(folders)+1
        folderindex = int(folderindex)
        if folderindex == 0:
            break
        if folderindex == 1:
            if folder:
                folder.pop()
        folder.append(folders[folderindex-2])
    return folder

def get_dataset(prompt,folder):
    datasets = gc.get_dir(folder)[0]
    print(
        '\n'.join(
            '{:d}\t:\t{}'.format(
                index+1,folder
            ) for index, folder in enumerate(
                datasets
            )
        )
    )
    dsindex = int(input('{}: '.format(prompt)))
    return folder + [datasets[dsindex-1]]

print('*' * 50)
print('select hwp calibration folder:')
print('*' * 50)

folder = get_folder('select calibration folder')

print('*' * 50)
print('select hwp calibration dataset:')
print('*' * 50)

path = get_dataset('select calibration dataset',folder)

angles, powers = gc.get_data_np(path)

while True:
    savefolder = os.path.join(saveroot,*folder)
    print(savefolder)
    if os.path.exists(savefolder):
        print('path exists.')
        mpl.rcParams['savefig.directory'] = savefolder

    print('*' * 50)
    print('select fluence curve folder:')
    print('*' * 50)

    dsfolder = get_folder('select fluence curve folder',folder)

    datasets = gc.get_dir(dsfolder)[0]

    show = {
        'y':True,
        'n':False
    }[input('show fits? (y/n): ')]

    amps = []
    ps = []
    for ds in datasets:
        angle = float(ds.split('-')[1].split(' ')[0])
        power = np.interp(angle,angles,powers)
        data = gc.get_data_np(dsfolder + [ds])
        fs, xs, ys = data[0], data[1], data[2]
        phase = fit.auto_phase(xs,ys,0.01)
        xps = fit.rephase(xs,ys,phase)
        if np.abs(xps).max() > xps.max():
            xps *= -1
        try:
            params, cov = fit.gaussian_fit(fs,xps,*fit.gaussian_guess(fs,xps))
            amp = params[2]
            if show:
                plt.plot(fs,xps,'.')
                plt.plot(fs,fit.gaussian(fs,*params))
                plt.show()
        except Exception:
            amp = 0.0    
        amps.append(amp)
        ps.append(power)
    plt.plot(ps,amps,'.')
    plt.xlabel('power (watts)')
    plt.ylabel('peak AM bolo signal (volts)')
    desc = input('enter description: ')
    plt.title('fluence curve, {}'.format(desc))
    plt.show()

    cont = {
        'y':True,
        'n':False
    }[input('continue? (y/n): ')]

    if not cont:
        break
