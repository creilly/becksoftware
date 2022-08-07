import wavemeter as wm
import powermeter as pm
import topo
import grapher.graphclient as gc
import numpy as np
import os

fringe_folder = r'C:\Users\labo\chris\software\libs\topo\data\fringes'
nfringes = 13

min_etalon = 6000
max_etalon = 7000
etalon_step = 5
etalon_width = 125

motor_step = 20

power_threshold = .3

wnummin = 2500
wnummax = 3500

day_folder = gc.get_day_folder()
for fringe in range(nfringes):
    fname = 'fringe-{:02d}.dat'.format(fringe)
    fringe_data = list(
        filter(
            lambda datum: int(datum[0]) % 20 == 0,
            np.loadtxt(
                os.path.join(fringe_folder,fname)
            )
        )
    )
    steps = len(fringe_data)
    for step, (motor, center_etalon, _) in enumerate(fringe_data):
        if motor % motor_step != 0:
            continue
        topo.set_motor_pos(motor*1e-3)
        center_etalon = int(center_etalon)
        etalons = list(
            filter(
                lambda etalon: etalon >= min_etalon and etalon <= max_etalon,
                range(
                    center_etalon-etalon_width,
                    center_etalon+etalon_width,
                    etalon_step
                )
            )
        )
        if not etalons:
            continue
        path = gc.add_dataset(
            day_folder + ['topo scan','fringe {:02d}'.format(fringe)],
            'motor {:04d} um'.format(int(motor)),
            ['etalon (steps)','power (watts)','wavenumber (cm-1)']
        )
        for etalon in etalons:
            print(
                '\t'.join(                        
                    (
                        'fringe:\t{:d} / {:d}'.format(fringe+1,nfringes),
                        'step:\t{:d} / {:d}'.format(step+1,steps),
                        'etalon:\t{:d} -> {:d} -> {:d}'.format(etalons[0],etalon,etalons[-1])
                    )
                )
            )
            topo.set_etalon_pos(etalon)
            if pm.get_power() < power_threshold:
                continue
            wnum = wm.get_wavenumber()
            if wnum < wnummin or wnum > wnummax:
                continue
            power = pm.get_power()
            gc.add_data(path,[etalon,power,wnum])
