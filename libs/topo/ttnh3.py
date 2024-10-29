import os, numpy as np

datafolder = os.path.join(os.path.dirname(__file__),'data','nh3')
ET, MO = 0, 1
fnd = {
    ET:'e',MO:'m'
}
fnfmt = 'fringe-data-{}-v-f.tsv'
def get_param(param,f):
    rows = np.loadtxt(
        os.path.join(datafolder,fnfmt.format(fnd[param]))
    )
    for row in rows:
        fmin, fmax, *cs = row
        order = len(cs) - 1
        if f > fmin and f < fmax:
            return sum(
                c * f ** (order - n) for n, c in enumerate(cs)
            )

def get_etalon(f):
    return get_param(ET,f)

def get_motor(f):
    return get_param(MO,f)