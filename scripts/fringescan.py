import topo
import powermeter as pm
import wavemeter as wm
from grapher import graphclient as gc
import numpy as np
from matplotlib import pyplot as plt

mmin = 9.10 # 7.250 # mm
mmax = 9.55 # # 9.250
dm1 = 0.0015 # 0.0005
dm2 = 0.015

emin = 6080 # 6000 # steps
emax = 6490 # 6750
de = 5

pmin = 0.5 # watts
pmin1 = 0.75 # watts
pmin2 = 0.55 # watts

es = range(emin,emax,de)

folder = gc.get_day_folder() + ['topo scans']

wnumfolder = gc.get_day_folder() + ['topo peaks']
wnumpath = gc.add_dataset(
    wnumfolder,
    'topo peaks',
    (
        'etalon position (steps)',
        'motor position (mm)',
        'wavenumber (cm-1)',
        'wavenumber error (cm-1)',
        'power (watts)'
    )
)

topo.set_diode_temperature(25.000)
topo.set_diode_current(95.0)
while not topo.get_diode_temperature_ready():
    print('waiting for diode temperature to settle...')

with pm.PMHandler() as pmh, wm.WavemeterHandler() as wmh:
    for e in es:
        topo.set_etalon_pos(e)
        path = gc.add_dataset(
            folder,
            'e {:04d} steps'.format(e),
            (
                'motor position (mm)',
                'power (watts)'
            )
        )
        ms = []
        ps = []
        m = mmin
        while m < mmax:            
            topo.set_motor_pos(m)
            p = pm.get_power(pmh)
            ms.append(m)
            ps.append(p)
            gc.add_data(path,(m,p))
            m += dm1 if p > pmin else dm2
        mode = 0
        fringes = []
        for m, p in zip(ms,ps):
            if mode == 0:
                if p < pmin1:
                    mode = 1
            if mode == 1:
                if p > pmin1:
                    fringes.append([])
                    mode = 2
            if mode == 2:
                if p > pmin1:
                    fringes[-1].append((m,p))
                if p < pmin2:
                    mode = 1
        if mode == 2:
            fringes.pop()
        for index, fringe in enumerate(fringes):
            msum = 0
            psum = 0
            for m, p in fringe:
                psum += p
                msum += m*p
            mavg = msum / psum
            plt.cla()
            plt.plot(*zip(*fringe),'.')
            plt.plot([mavg]*2,[0,max(list(zip(*fringe))[1])],color='black')
            plt.xlabel('motor position (mm)')
            plt.ylabel('power')
            title = 'e {:d}, f {:d}'.format(e,index)
            plt.title(title)
            plt.savefig('{}.png'.format(title))
            topo.set_motor_pos(mavg)
            M = 20
            N = 20
            n = 0
            pavg = 0
            wavg = 0
            wvar = 0
            while n < M + N:
                n += 1
                while True:
                    try:
                        w = wm.get_wavenumber(wmh)
                        break
                    except:
                        continue
                print(index,n,w)
                if n > M:
                    p = pm.get_power(pmh)
                    wavg += w
                    wvar += w**2
                    pavg += p
            wavg /= N
            wvar /= N
            wstd = np.sqrt(wvar - wavg**2)
            pavg /= N
            gc.add_data(
                wnumpath,
                (
                    e,
                    mavg,
                    wavg,
                    wstd,
                    pavg
                )
            )     
