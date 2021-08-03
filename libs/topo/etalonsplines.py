import numpy as np
import os
from grapher import graphclient as gc
from topotools import _generate_spline, _data_folder, _write_spline, _etalon_splines_folder, _etalon_bounds_fname
from matplotlib import pyplot as plt

_etalon_spline_fname_fmt = 'fringe_{:02d}.dat'

gcfolder = ['2021','02','18','topo analysis','etalon calibration']

fringedatasets = gc.get_dir(gcfolder)[0]

wbounds = []
for fringeds in fringedatasets:
    fringenum = int(fringeds[-6:-4])
    wnums, etalons = zip(*sorted(zip(*gc.get_data(gcfolder+[fringeds]))))
    wbounds.append([fringenum,wnums[0],wnums[-1]])
    smoothing = 0 / 2**-1 + 1 / 2**0 + 1 / 2**1 + 0 / 2**2 + 0 / 2**3 + 1 / 2**4 + 1 / 2**5
    spline = _generate_spline(wnums,etalons,smoothing=smoothing)
    color = plt.plot(wnums,etalons,'.')[0].get_color()
    plt.plot(wnums,spline(wnums),color=color)
    # _write_spline(
    #     _fmt_etalon_fname(
    #         _etalon_spline_fname_fmt.format(fringenum),True
    #     ),spline
    # )
plt.xlabel('wavenumber (cm-1)')
plt.ylabel('etalon position (steps)')
plt.title('etalon fringe splines')
plt.show()
# with open(
#     _fmt_etalon_fname(
#         _etalon_bounds_fname,False
#     ),'w'
# ) as f:
#     f.write(
#         '\n'.join(
#             ['fringe num\twnum min (cm-1)\twnum max (cm-1)']
#             +
#             ['{0:02d}\t{1:f}\t{2:f}'.format(*wbound) for wbound in wbounds]
#         )
#     )

