import os, numpy as np

datafolder = os.path.join(os.path.dirname(__file__),'data','nh3')
ET, MO = 0, 1
fnd = {
    ET:'e',MO:'m'
}
fnfmt = 'fringe-data-{}-v-f.tsv'
epsilonf = 0.001 # cm-1

def eval_poly(cs,f):
    order = len(cs) - 1
    return sum(
        c * f ** (order - n) for n, c in enumerate(cs)
    )
def get_param(param,f):
    rows = np.loadtxt(
        os.path.join(datafolder,fnfmt.format(fnd[param]))
    )
    for row in rows:
        fmin, fmax, *cs = row        
        if f > fmin and f < fmax:
            p = eval_poly(cs,f)
            dpdf = (eval_poly(cs,f+epsilonf) - p)/epsilonf
            return p, dpdf

def get_etalon(f):
    return get_param(ET,f)

def get_motor(f):
    return get_param(MO,f)