import grapher.graphclient as gc
import numpy as np
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit

folder = ['2021','02','18','topo analysis','etalon calibration']
fringes = range(1,12)

deltam = 5

def get_data():
    filesd = {}
    files, _ = gc.get_dir(folder)
    for file in files:
        filesd[
            int(
                file.split(' ')[1].split('.')[0]
            )
        ] = file
    return [
        gc.get_data_np(folder + [filesd[fringe]]) for fringe in fringes
    ]

def wnum(m,etalon,eo,dphide,no,fsr,ko,dn,d2phide2):
    k_rough = wnum_rough(m,etalon,eo,dphide,no,fsr,ko,dn,d2phide2)
    return (
        ko + (m-deltam)*fsr/(1+dn*(k_rough-ko))
    ) * np.sqrt(
        1 - (
            np.sin(
                dphide * (etalon - eo)
                +
                d2phide2 * (etalon - eo)**2
                # +
                # d4phide4 * (etalon - eo)**4
            ) / (no*(1+dn*(k_rough-ko)))
        )**2
    )    

def wnum_rough(m,etalon,eo,dphide,no,fsr,ko,dn,d2phide2):
    return (
        ko + (m-deltam)*fsr
    ) * np.sqrt(
        1 - (
            np.sin(
                dphide * (etalon - eo)
                +
                d2phide2 * (etalon - eo)**2
                # +
                # d4phide4 * (etalon - eo)**4
            ) / no
        )**2
    )

dsinde = 5.233e-4
def wnum_sinebar_rough(m,etalon,eo,no,fsr,ko,dn,epsilon):
    return (
        ko + (m-deltam)*fsr
    ) * np.sqrt(
        1 - (
            dsinde * (
                1 * (etalon - eo)
                +
                epsilon * (etalon - eo)**2
            ) / no
        )**2
    )

def wnum_sinebar(m,etalon,eo,no,fsr,ko,dn,epsilon):
    k_rough = wnum_sinebar_rough(m,etalon,eo,no,fsr,ko,dn,epsilon)
    return (
        ko + (m-deltam)*fsr/(1+dn*(k_rough-ko))
    ) * np.sqrt(
        1 - (
            dsinde * (
                1 * (etalon - eo)
                +
                epsilon * (etalon - eo)**2
            ) / ( no * (1 + dn*(k_rough-ko)) )
        )**2
    )

def get_etalon(m,n):
    return fringedata[m][1][n]

def get_wnum(m,n):
    return fringedata[m][0][n]

def fit(X,*args):
    Y = []
    for (m,n) in X:
        n,m = int(n), int(m)
        Y.append(
            wnum_sinebar(
                m,get_etalon(m,n),*args
            )
        )
    return Y
fringedata = get_data()
s = sum(
    [
        [
            (
                (m,n),
                get_wnum(m,n)
            ) for n in range(len(fringedata[m][0]))
        ] for m in range(len(fringedata))
    ],
    []
)
X, Y = zip(*s)

epsilon, ko, fsr, eo, dphide, no, d2phide2, d3phide3, d4phide4, dk, dn = 'epsilon', 'ko', 'fsr', 'eo', 'dphide', 'no', 'd2phide2', 'd3phide3', 'd4phide4', 'dk', 'dn'
model_params = {
    ko:3.045e+03, #ko:2.783702e+03,
    fsr:4.338465e+01,
    eo:7.388177e+03,
    dphide:3.532527e-04,
    no:2.075261e+00,
    d2phide2:0,
    d3phide3:0,
    d4phide4:0,
    dk:0,
    dn:0,
    epsilon:0
}

guesses = tuple(
    map(
        model_params.get,
        (eo,no,fsr,ko,dn,epsilon)
    )
)

params, cov = curve_fit(fit,X,Y,guesses)
print(params)
etalons = []
k_guesses = []
for m, n in X:
    etalon = get_etalon(m,n)
    etalons.append(etalon)
    k_guesses.append(wnum_sinebar(m,etalon,*params))
    
plt.plot(etalons,Y,'.')
plt.plot(etalons,k_guesses)
plt.show()
    
    
