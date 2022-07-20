from grapher import graphclient as gc
import numpy as np
from matplotlib import pyplot as plt
from topo.topotools import get_wnum

nfringes = 13

omit_fringes = (0,)

outliers = ((7,8620),)

fringes = [
    fringe for fringe in range(nfringes) if fringe not in omit_fringes
]

root_folder = ['2021','02','18','topo scan']

delta_etalon = 40
min_points = 10

fringe_motors = []
fringe_calib_wnums = []
fringe_calib_etalons = []
for fringe in fringes:
    print(fringe)
    folder = root_folder + ['fringe {:02d}'.format(fringe)]
    files, _ = gc.get_dir(folder)
    motors = []
    calib_wnums = []
    calib_etalons = []
    for fname in files:
        path = folder + [fname]
        motor = int(fname.split(' ')[1])
        if (fringe,motor) in outliers:
            continue
        data = gc.get_data_np(path)
        if not data: continue
        etalons, powers, wnums = gc.get_data_np(path)
        max_index = powers.argmax()
        max_etalon = etalons[max_index]
        peak_etalons, peak_powers, peak_wnums = map(
            np.array,
            zip(
                *[
                    (etalon, power, wnum) for etalon, power, wnum in zip(etalons,powers,wnums)
                if abs(etalon-max_etalon) < delta_etalon
                ]
            )
        )
        if len(peak_etalons) < min_points:
            continue
        a, b, c = np.polyfit(peak_etalons,peak_powers,2)
        peak_etalon = -b / (2*a)
        if peak_etalon < peak_etalons.min() or peak_etalon > peak_etalons.max():
            continue
        m, b = np.polyfit(peak_etalons,peak_wnums,1)
        peak_wnum = m * peak_etalon + b
        motors.append(motor)
        calib_wnums.append(peak_wnum)
        calib_etalons.append(peak_etalon)
    fringe_motors.append(motors)
    fringe_calib_wnums.append(calib_wnums)
    fringe_calib_etalons.append(calib_etalons)

# root_folder = ['2021','02','18','topo analysis','wavenumber calibration']
# fringe = 1
# for motors, wnums in zip(fringe_motors,fringe_calib_wnums):
#     path = gc.add_dataset(root_folder,'fringe {:02d}'.format(fringe),['motor (mm)','wavenumber (cm-1)'])
#     for motor, wnum in zip(motors,wnums):
#         gc.add_data(path,[motor,wnum])
#     fringe += 1
root_folder = ['2021','02','18','topo analysis','etalon calibration']
fringe = 1
for wnums, etalons in zip(fringe_calib_wnums,fringe_calib_etalons):
    path = gc.add_dataset(
        root_folder,
        'fringe {:02d}'.format(fringe),
        ['wavenumber (cm-1)','etalon position (steps)']
    )
    for wnum, etalon in zip(wnums,etalons):
        gc.add_data(path,[wnum,etalon])
    fringe += 1
