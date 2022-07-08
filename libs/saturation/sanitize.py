from grapher import graphclient as gc
from matplotlib import pyplot as plt
import numpy as np
import fit
from scipy.optimize import curve_fit
import sympy
from sympy.physics.quantum.cg import CG # (j1, m1, j2, m2, j3, m3)
import powercalib
import hitran
import os
import json

debug = True

phimin = 3.5
phimax = 52.5
phio = 6.089

FC_NAME = 'fluence curves'
FS_NAME = 'frequency scans'

FC, FS = 0, 1
MODES = (FC,FS)
modenamed = {
    FC:'fluence curves',
    FS:'frequency scans'
}

def lookup_line(line,datasets):
    for dataset in datasets:
        _line = dataset.split('-',1)[-1]
        if _line == line:
            return dataset
    return None

DPHI = 0.01 # radians
def rephase_data(x,y):
    phi = fit.auto_phase(x,y,DPHI)
    z = fit.rephase(x,y,phi)
    if max(np.abs(z)) > max(z):
        z *= -1
    return z

def rescale_data(z):
    return z / z.sum()

DFDW = 30e3 # MHz / cm-1
def rescale_frequency(zs,fs,ws):
    max_index = zs.argmax()
    fmax = fs[max_index]
    wmax = ws[max_index]
    fs -= fmax
    ws -= wmax
    ws *= DFDW # MHz
    slope, intercept = np.polyfit(fs,ws,1)
    fs *= slope
    return fs

N_BASELINE = 10
def get_fit(fs,irs):
    iro = np.average(sorted(irs)[:N_BASELINE])
    indices = np.arange(len(fs))
    def fit(_,mu,sigma,amp,offset):        
        return [
            amp * np.exp(
                -1/2*(                    
                    (fs[i]-mu)/sigma
                )**2
            ) + offset*irs[i]/iro
            for i in indices
        ]
    return iro, fit

SIGMA_O = 10.0 # MHz
def remove_baseline(fs,zs,irs):
    zmin = zs.min()
    zmax = zs.max()

    mu = 0.0 # MHz
    sigma = SIGMA_O # MHz    
    amp = zmax - zmin
    offset = zmin

    guess = (mu,sigma,amp,offset)

    iro, curve = get_fit(fs,irs)

    params, cov = curve_fit(curve,fs,zs,guess)
    mu, sigma, amp, offset = params    

    fs -= mu

    if debug:
        omegas = fs * np.pi * 2
        print('')
        plt.plot(omegas,zs,'.',label='data')
        plt.plot(omegas,curve(fs,0.0,sigma,amp,offset),label='fit')    
        plt.xlabel('radial frequency (rads / microsec, calibrated)')
        plt.ylabel('lockin signal (volts)')
        plt.ylim(ymin = 0)        
        plt.legend()
        plt.title('with offset')
        plt.show()
    zs -= offset*irs/iro
    if debug:        
        plt.plot(omegas,zs,'.',label='data')
        plt.plot(omegas,curve(fs,0.0,sigma,amp,0.0),label='fit')    
        plt.legend()
        plt.xlabel('radial frequency (rads / microsec, calibrated)')
        plt.ylabel('lockin signal (volts)')        
        plt.title('background subtracted')
        plt.show()
    return fs, zs, sigma

CLIP_FACTOR = 3.0
def clip_data(fs,zs,irs,pc,sigma,phio):
    deltaf = CLIP_FACTOR * sigma
                
    omega_clippeds = []
    z_clippeds = []
    power_clippeds = []

    for f, z, ir in zip(fs,zs,irs):
        if f < -deltaf:
            continue
        if f > +deltaf:
            break
        omega_clippeds.append(2.0 * np.pi * f)
        z_clippeds.append(z)
        power_clippeds.append(pc(phio,ir))
    return map(np.array,(omega_clippeds,z_clippeds,power_clippeds))

def hitran_lookup(line,cgcd):
    mol, branch, j, sym = map(int,line.split('.')[0].split(' '))
    j1 = j
    j2 = j + branch
    if j1 not in cgcd or j2 not in cgcd[j1]:
        add_cgcs(j1,j2,cgcd)
    glq = (
        (0,0,0,0),'A1',1
    )
    guq = (
        (0,0,1,0),'F2',1
    )
    mol = 6
    iso = 1
    return hitran.search_db(mol,iso,glq,guq,branch,j,sym), j1, j2

def add_cgcs(j1,j2,cgcd):
    m = 0
    while True:
        if m > j1:
            break
        cgc_sym = CG(
            j1,m,1,0,j2,m
        )
        cgc = float(np.abs(sympy.N(cgc_sym.doit())))    
        cgcd.setdefault(j1,{}).setdefault(j2,{})[m] = cgc
        m += 1
modefolderd = {
    FC:'fc',FS:'fs'
}
cgcfname = 'cgc'
metadatafname = 'md'

def_outfolder = 'data'
def sanitize_experiment(
    pcpath,phimin,phimax,phio,
    datafolder,lines,outfolder=def_outfolder,_debug = None
):
    if not os.path.exists(outfolder):
        os.mkdir(outfolder)
    for mode in (FC,FS):
        mf = os.path.join(outfolder,modefolderd[mode])
        if not os.path.exists(mf):
            os.mkdir(mf)
    cgcd = {}
    metadata = []
    if _debug is not None:
        global debug
        debug = _debug
    pc = powercalib.get_power_calib(pcpath,phimin,phimax)    
    datasetsd = {
        mode:gc.get_dir(datafolder + [modenamed[mode]])[0] for mode in MODES
    }
    for lineindex, line in enumerate(lines):
        linemd = {}
        metadata.append(linemd)
        ht_line, j1, j2 = hitran_lookup(line,cgcd)
        if debug or True:
            print(
                'line : {}'.format(line),
                '\t|\t',
                'htline : {}'.format(
                    ' ~ '.join(
                        map(
                            lambda s: s.replace(hitran.NBS,' '),
                            ht_line
                        )
                    )
                )
            )
        htd = hitran.lookup_line(ht_line)
        wavenumber = htd[hitran.WNUM]
        einstein_coeff = htd[hitran.EIN_COEFF]
        linemd['wavenumber'] = (wavenumber,'cm-1')
        linemd['einstein coefficient'] = (einstein_coeff,'s-1')
        linemd['j1'] = j1
        linemd['j2'] = j2
        linemd['grapher name'] = line
        linemd['hitran line'] = ht_line        
        lengths = {}
        linemd['lengths'] = lengths
        for mode in MODES:
            datasets = datasetsd[mode]
            dataset = lookup_line(line,datasets)
            if dataset is None:
                raise Exception('dataset not found.')
            path = datafolder + [modenamed[mode], dataset]
            if mode is FC:
                phis, \
                    xons, yons, irons, wons, \
                        xoffs, yoffs, iroffs, woffs, \
                            *_ = gc.get_data_np(path)
                zs = rephase_data(xons-xoffs,yons-yoffs)
                zs = rescale_data(zs)
                ps = pc(phis,irons)
                omegas = np.zeros(zs.shape)
                if debug:
                    plt.plot(ps,zs,'.')                    
                    plt.xlabel('power (watts)')
                    plt.ylabel('lockin signal (normed)')                    
                    plt.title('normed fluence curve')               
                    plt.show()
            if mode is FS:
                fs, xs, ys, irs, ws = gc.get_data_np(path)                
                zs = rephase_data(xs,ys)              
                fs = rescale_frequency(zs,fs,ws)                
                fs, zs, sigma = remove_baseline(fs,zs,irs)                
                omegas, zs, ps = clip_data(fs,zs,irs,pc,sigma,phio)
                zs = rescale_data(zs)
                if debug:
                    plt.plot(omegas,zs,'.')                    
                    plt.xlabel('radial frequency (rads / microsec, calibrated)')
                    plt.ylabel('lockin signal (normed)')
                    plt.title('clipped')                    
                    plt.show()            
            lengths[mode] = len(zs)
            np.savetxt(
                os.path.join(outfolder,modefolderd[mode],'{:03d}.tsv'.format(lineindex)),
                np.vstack([omegas,ps,zs]).transpose()
            )    
    with open(os.path.join(outfolder,'{}.json'.format(metadatafname)),'w') as f:
        json.dump(metadata,f,indent=2)
    with open(os.path.join(outfolder,'{}.json'.format(cgcfname)),'w') as f:
        json.dump(cgcd,f,indent=2)

def load_json(folder,name):
    with open(os.path.join(folder,'.'.join((name,'json'))),'r') as f:
        return json.load(f)

def load_cgc(folder=def_outfolder):
    return {
        int(j1):{
            int(j2):{
                int(m):cgc
                for m, cgc in j2d.items()
            } for j2, j2d in j1d.items()
        } for j1, j1d in load_json(folder,cgcfname).items()
    }

def load_metadata(folder=def_outfolder):
    return load_json(folder,metadatafname)

def load_data(line_index,mode,folder=def_outfolder):
    fname = os.path.join(
        folder,modefolderd[mode],'{:03d}.tsv'.format(line_index)
    )    
    return np.loadtxt(fname)

if __name__ == '__main__':
    # import pprint
    # cgcd = load_cgc('data')
    # pprint.PrettyPrinter(4).pprint(cgcd)    
    # exit()
    pcpath = ['2022','05','25','00001-hwp scan.tsv']
    datafolder = ['2022','05','25']
    phimin = 3.5
    phimax = 52.5
    phio = 6.089
    lines = [
        ds.split('-',1)[-1]
        for index, ds in 
        enumerate(gc.get_dir(datafolder + [modenamed[FC]])[0])
        if index not in (11,)
    ]
    sanitize_experiment(pcpath,phimin,phimax,phio,datafolder,lines,_debug=False)