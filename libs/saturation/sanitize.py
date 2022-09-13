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
import datetime

debug = True

FC_NAME = 'fluence curves'
FS_NAME = 'frequency scans'

FC, FS = 0, 1
MODES = (FC,FS)
modenamed = {
    FC:'fluence curves',
    FS:'frequency scans'
}

DTHETA = 0.01 # radians

# takes in an array z and returns a pair (zscale, zp)
# where zscale is a scalar and 
# zp is an array and
# z = zscale * zp
def rescale_data(z):
    return z.sum(), z / z.sum()

DFDW = 30e3 # MHz / cm-1
def rescale_frequency(zs,fs,ws,freqcalib):
    max_index = zs.argmax()
    fmax = fs[max_index]
    fs -= fmax
    if freqcalib:
        wmax = ws[max_index]        
        ws -= wmax
        ws *= DFDW # MHz
        slope, intercept = np.polyfit(fs,ws,1)
        print('slope:',slope)
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

def fit_baseline(fs,zs,irs):
    zmin = zs.min()
    zmax = zs.max()

    # mu = 0.0 # MHz
    mu = fs[zs.argmax()] # MHz
    sigma = SIGMA_O # MHz    
    amp = zmax - zmin
    offset = zmin

    guess = (mu,sigma,amp,offset)

    iro, curve = get_fit(fs,irs)

    params, cov = curve_fit(curve,fs,zs,guess)
    
    return iro, params    

SIGMA_O = 10.0 # MHz
def remove_baseline(fs,zs,irs):
    iro, params = fit_baseline(fs,zs,irs)

    mu, sigma, amp, offset = params    

    fs -= mu

    # if debug:
    #     omegas = fs * np.pi * 2
    #     print('')
    #     plt.plot(omegas,zs,'.',label='data')
    #     plt.plot(omegas,curve(fs,0.0,sigma,amp,offset),label='fit')    
    #     plt.xlabel('radial frequency (rads / microsec, calibrated)')
    #     plt.ylabel('lockin signal (volts)')
    #     plt.ylim(ymin = 0)        
    #     plt.legend()
    #     plt.title('with offset')
    #     plt.show()
    zs -= offset*irs/iro
    # if debug:        
    #     plt.plot(omegas,zs,'.',label='data')
    #     plt.plot(omegas,curve(fs,0.0,sigma,amp,0.0),label='fit')    
    #     plt.legend()
    #     plt.xlabel('radial frequency (rads / microsec, calibrated)')
    #     plt.ylabel('lockin signal (volts)')        
    #     plt.title('background subtracted')
    #     plt.show()
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

modefolderd = {
    FC:'fc',FS:'fs'
}
cgcfname = 'cgc'
metadatafname = 'md'

def_outfolder = 'data'
def_imagefolder = 'images'
def fmt_title(desc,lineindex,htline):
    return '\n'.join(
        [
            '{} - {:03d}'.format(desc,lineindex),
            hitran.fmt_line(htline)
        ]
    )
def sanitize_experiment(
    pcpath,phimin,phimax,phio,
    lines,outfolder=def_outfolder,imagefolder=def_imagefolder,
    autophase = True,freqcalib = False    
):
    for folder in (outfolder,imagefolder):
        if not os.path.exists(folder):
            os.makedirs(folder)
    for mode in (FC,FS):
        mf = os.path.join(outfolder,modefolderd[mode])
        if not os.path.exists(mf):
            os.makedirs(mf)
    cgcd = {}
    metadata = []    
    irpdo, (params,cov) = powercalib.get_fit_params(pcpath,phimin,phimax)
    pc = powercalib.get_power_calib(irpdo,params)
    for lineindex, (htline, lined) in enumerate(lines.items()):        
        linemd = {}
        metadata.append(linemd)
        j1, sym1, l1 = hitran.parse_lq(htline[hitran.LLQ])
        j2, sym2, l2 = hitran.parse_lq(htline[hitran.ULQ])
        if j1 not in cgcd or j2 not in cgcd[j1]:
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
        if debug or True:
            print(                
                'htline : {}'.format(
                    ' ~ '.join(
                        map(
                            lambda s: s.replace(hitran.NBS,' '),
                            htline
                        )
                    )
                )
            )
        htd = hitran.lookup_line(htline)
        wavenumber = htd[hitran.WNUM]
        einstein_coeff = htd[hitran.EIN_COEFF]
        linemd['wavenumber'] = (wavenumber,'cm-1')
        linemd['einstein coefficient'] = (einstein_coeff,'s-1')
        linemd['j1'] = j1
        linemd['j2'] = j2
        linemd['grapher datasets'] = lined
        linemd['hitran line'] = htline
        lengths = {}        
        linemd['lengths'] = lengths
        scales = {}
        linemd['scales'] = scales
        for mode in MODES:            
            path = lined[mode]
            if mode is FC:
                *folder, dsname = path
                dshead, dstail = os.path.splitext(dsname)
                mdname = '.'.join([dshead,'bmd'])
                mdpath = folder + [mdname]
                graphermd = gc.get_metadata(mdpath)
                signalgain = graphermd['bolometer gain'][0]
                refd = graphermd['sensitivity']
                refgain = refd['bolo gain'][0]
                refamp = refd['measurement']['r'][0]
                sensfactor = refgain / signalgain / refamp 
                linemd['sensitivity factor'] = sensfactor
                phis, \
                    xons, yons, irons, wons, \
                        xoffs, yoffs, iroffs, woffs, \
                            *_ = gc.get_data_np(path)
                if autophase:
                    xdiffs = xons-xoffs
                    ydiffs = yons-yoffs
                    theta = fit.auto_phase(xdiffs,ydiffs,DTHETA)                    
                    zs = fit.rephase(xdiffs,ydiffs,theta)
                    if zs.sum() < 0:
                        zs *= -1
                        theta += (+1 if theta < np.pi else -1) * np.pi
                    thetadegs = np.rad2deg(theta)
                    print('phase:',thetadegs)
                    
                else:
                    zs = xons - xoffs
                    thetadegs = 0.0
                linemd['software phase'] = (thetadegs,'degrees')
                zscale, zs = rescale_data(zs)
                ps = pc(phis,irons)
                omegas = np.zeros(zs.shape)
                if debug:
                    plt.plot(ps,zs,'.')                    
                    plt.xlabel('power (watts)')
                    plt.ylabel('lockin signal (normed)')                    
                    plt.title(fmt_title('normed fluence curve',lineindex,htline))
                    plt.savefig(os.path.join(imagefolder,'{:03d}-{:d}.png'.format(lineindex,FC)))
                    plt.cla()
            if mode is FS:
                fs, xs, ys, irs, ws = gc.get_data_np(path)                
                if autophase:
                    zs = fit.rephase(xs,ys,theta)
                else:
                    zs = xs                
                fs = rescale_frequency(zs,fs,ws,freqcalib)
                fs, zs, sigma = remove_baseline(fs,zs,irs)                
                omegas, zs, ps = clip_data(fs,zs,irs,pc,sigma,phio)                
                zscale, zs = rescale_data(zs)
                if debug:
                    plt.plot(omegas,zs,'.')                    
                    plt.xlabel('radial frequency (rads / microsec, {} calibrated)'.format('wm' if freqcalib else 'tc'))
                    plt.ylabel('lockin signal (normed)')
                    plt.title(fmt_title('frequency scan (clipped)',lineindex,htline))                        
                    plt.tight_layout()
                    plt.savefig(os.path.join(imagefolder,'{:03d}-{:d}.png'.format(lineindex,FS)))
                    plt.cla()            
            lengths[mode] = len(zs)
            scales[mode] = zscale
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
    phimin = 16.0
    phimax = 60.0
    phio = 17.0   
    pcpath = ['2022','06','30','00000-hwp scan.tsv']

    datafolder = ['2022','06','30']
    
    lines = {}

    folders = {
        mode:datafolder + [modenamed[mode]]
        for mode in (FC,FS)
    }    
    fcfolder = folders[FC]
    fc_datasets, _, fc_metadatas = gc.get_dir(fcfolder)
    dsnames = {}
    for rawdsname, mdname in zip(fc_datasets,fc_metadatas):
        dsname = rawdsname.split('-',1)[-1].split('.tsv')[0]
        if dsname in dsnames:
            print('duplicate line detected')
        dsnames[dsname] = (
            rawdsname,
            datetime.datetime.fromisoformat(
                gc.get_metadata(fcfolder + [mdname])['_created']
            ).timestamp()
        )
    fsfolder = folders[FS]
    fs_datasets, _, fs_metadatas = gc.get_dir(fsfolder)
    for dsname, (rawdsname, timestamp) in dsnames.items():
        dsmatch = None
        for _rawdsname, mdname in zip(fs_datasets,fs_metadatas):
            _dsname = _rawdsname.split('-',1)[-1].split('.tsv')[0]
            if _dsname == dsname:
                _timestamp = datetime.datetime.fromisoformat(
                    gc.get_metadata(fsfolder + [mdname])['_created']
                ).timestamp()
                print('fc',rawdsname,'fs',_rawdsname,'dt',timestamp-_timestamp)
                if _timestamp > timestamp:
                    break
                dsmatch = rawdsname
        if dsmatch is None:
            raise Exception('no fs match found')
        lineinfo = list(map(int,dsname.split(' ')))
        if len(lineinfo) == 5:
            mol, b, j, ll, ul = lineinfo
            if ll == 8 and ul == 10:
                ll = 10
                ul = 81
            molecule = 6
            iso = 1
            glq, guq = {
                3:([0,0,1,0],[0,0,2,0]),
                4:([1,0,0,0],[1,0,1,0])
            }[mol]
            glevel = 1
            glsym, gusyms = {
                3:('F2',('E','F2')),
                4:('A1',('F2',))
            }[mol]            
            j1 = j
            j2 = j + b
            for gusym in gusyms:
                htline = hitran.search_db(6,1,(glq,glsym,glevel),(guq,gusym,glevel),b,j,ll=ll,ul=ul)
                if htline is not None:
                    break
            if htline is None:
                raise Exception('line not found!','dsname:','<{}>'.format(dsname))
        else:
            raise Exception('need to handle lengths != 5')
        lines[tuple(htline)] = {
            FC:fcfolder + [rawdsname],
            FS:fsfolder + [_rawdsname]
        }    
    sanitize_experiment(pcpath,phimin,phimax,phio,lines,_debug=True)
    sanitize_experiment()