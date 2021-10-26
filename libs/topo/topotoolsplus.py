import os
from grapher import graphclient as gc
import hitran

folder = ['2021','10','13','lut']

branchd = {
    hitran.P:'P',
    hitran.Q:'Q',
    hitran.R:'R'
}

# returns:
    # 1. center wavelength (cm-1)
    # 2. slope of etalon vs. wavelength fit (steps per cm-1)
    # 3. intercept of etalon vs. wavelength fit (steps)
    # 4. slope of motor vs. wavelength fit (mm per cm-1)
    # 5. intercept of motor vs. wavelength fit (mm)
def get_line(branch,j,A):
    f = folder + [
        branchd[branch],'j {:d}'.format(j),'A{:d}'.format(A)
    ]
    return list(
        zip(
            *gc.get_data(
                f + [
                    gc.get_dir(
                        f
                    )[0][0]
                ]
            )
        )
    )[0]

# skip_rows = 1

# folder = os.path.join(os.path.dirname(__file__),'data','lut')
# fname = 'lut.tsv'
# path = os.path.join(folder,fname)

# peaks = [
#     [
#         f(d)
#         for f, d in zip(
#             [lambda x: int(float(x))] + [float]*4,
#             l.split('\t')
#         )
#     ]
#     for l in
#     open(path,'r').read().strip().split('\n')[skip_rows:]
# ]

# def lookup_wnum(wo):
#     dws = [
#         abs(w-wo) for e,m,w,dw,p in peaks
#     ]
#     return min(zip(dws,peaks),key=lambda pair: pair[0])[1]
