import argparse
from grapher import graphclient as gc
from matplotlib import pyplot as plt
from saturation import sanitize
import hitran
import datetime

ap = argparse.ArgumentParser()
ap.add_argument('-d','--data',help='data folder [e.g. "2022-08-01" (no quotes)]')
ap.add_argument('-p','--power',help='power calib folder [e.g. "2022-08-01" (no quotes)]')
ap.add_argument('-i','--index',help='power calib dataset index',type=int)
ap.add_argument('-f','--freq',choices=['y','n'],help='perform frequency calibration?')
ap.add_argument('-a','--autophase',choices=['y','n'],help='perform autophasing?')
ap.add_argument('-l','--lines',help='hitran lines to exclude, by freq scan dataset index (e.g. "2,4,5,10-15,21")')
ap.add_argument('-s','--datasets',help='datasets to exclude, by freq scan dataset index (e.g. "2,4,5,10-15,21")')
ap.add_argument('-x','--phimax',help='max angle of power calib fit range',type=float)
ap.add_argument('-n','--phimin',help='min angle of power calib fit range',type=float)
ap.add_argument('-o','--phio',help='peak angle of power calib fit range',type=float)
args = ap.parse_args()

DATA, POWER = 0, 1
pathkeys = (DATA,POWER)
pathnames = {
    DATA:'data',
    POWER:'power calib'
}
pathargs = {
    DATA:'data',
    POWER:'power'
}

def get_folder_prompt(mode):
    def _get_folder_prompt(datum):
        return 'enter {} {}: '.format(mode,datum)
    return _get_folder_prompt

def get_folder(mode):
    fp = get_folder_prompt(pathnames[mode])
    year = input(fp('year'))
    month = input(fp('month')).rjust(2,'0')
    day = input(fp('day')).rjust(2,'0')
    return [year,month,day]

paths = {}
for pathkey in pathkeys:
    arg = getattr(args,pathargs[pathkey])
    if arg is not None:
        path = arg.split('-')
        print('{} folder: [{}]'.format(pathnames[pathkey],','.join(path)))
        paths[pathkey] = path
        continue
    if pathkey == POWER:
        different = input(
            'is power calib file a different day (y/[n])?: '
        )
        if not different or different.lower()[0] == 'n':
            paths[pathkey] = paths[DATA]
            continue 
    paths[pathkey] = get_folder(pathkey)

pcfolder = paths[POWER]
pcds = gc.get_dir(pcfolder)[0]
def parse_number_list(rawinput):
    slices = rawinput.split(',')
    ranges = [list(range(s[0],s[-1]+1)) for s in [list(map(int,t.split('-'))) for t in slices if t.strip()]]
    return sum(ranges,[])

def fmt_dir(fs):
    return '\n'.join(
        '{: 2d}\t:\t{}'.format(
            int(index),name
        ) for index, name in [
            ds.split('-',1) for ds in fs
        ]
    )
pci = args.index
if pci is None:    
    print(fmt_dir(pcds))
    pci = int(input('select power calib dataset: '))

pcpath = pcfolder + [pcds[pci]]
phinames = ['phi min','phi max','phi peak']
phiargs = ['phimin','phimax','phio']
needphi = any([getattr(args,arg) is None for arg in phiargs])
if needphi:
    thetas, powers, pds = gc.get_data_np(pcpath)
    plt.plot(thetas,powers)
    plt.show(block=False)
phis = []
for name, arg in zip(phinames,phiargs):
    arg = getattr(args,arg)    
    if arg is None:
        phis.append(float(input('enter {}: '.format(name))))
    else:
        phi = arg
        print('{}: {:.2f}'.format(name,phi))        
        phis.append(arg)        
phimin, phimax, phio = phis
if needphi:
    plt.close()

dfolder = paths[DATA]
fsfolder = [*dfolder,sanitize.modenamed[sanitize.FS]]
fcfolder = [*dfolder,sanitize.modenamed[sanitize.FC]]
dds, _, dmd = gc.get_dir(fsfolder)

skipindices = []
while True:
    if args.lines is not None:
        skipindices = parse_number_list(args.lines)
        print('line skip indices:',args.lines)
        break
    print(
        fmt_dir(
            [
                ds for n, ds in enumerate(dds) if n not in skipindices
            ]
        )
    )
    skipindicesp = input('enter *ht lines* to skip by freq scan index (enter to continue): ')
    if not skipindicesp:
        break    
    skipindicesp = parse_number_list(skipindicesp)
    for skipindex in skipindicesp:
        root, leaf = dds[skipindex].split('-',1)
        for dsp in dds:
            rootp, leafp = dsp.split('-',1)            
            indexp = int(rootp)
            if leafp == leaf:                
                if indexp not in skipindices:
                    skipindices.append(indexp)
while True:
    if args.datasets is not None:
        skipindicesp = parse_number_list(args.datasets)
        skipindices += skipindicesp
        print('skip indices:',args.datasets)
        break
    print(
        fmt_dir(
            [
                ds for n, ds in enumerate(dds) if n not in skipindices
            ]
        )
    )
    skipindex = input('enter *datasets* to skip by freq scan index (enter to continue): ')
    if not skipindex:
        break
    skipindex = int(skipindex)
    skipindices.append(skipindex)

fsdsl, _, fsmdl = gc.get_dir(fsfolder)
fcdsl, _, fcmdl = gc.get_dir(fcfolder)

def get_htline(metadata,dsname):
    if 'hitran line' not in metadata:
        dsindex, dsname = dsname.split('-',1)
        dsname, ext = dsname.split('.')
        nu, branch, j, ll, ul = map(int,dsname.split(' '))
        if nu == 0:
            lq = [0,0,0,0]
            lsym = 'A1'
            lgl = 1
            lgq = (lq,lsym,lgl)

            uq = [0,0,1,0]
            usym = 'F2'
            ugl = 1
            ugq = (uq,usym,ugl)

            ugqs = (ugq,)

        if nu == 3:
            lq = [0,0,1,0]
            lsym = 'F2'
            lgl = 1
            lgq = (lq,lsym,lgl)

            uq1 = [0,0,2,0]
            usym1 = 'F2'
            ugl1 = 1
            ugq1 = (uq1,usym1,ugl1)

            uq2 = [0,0,2,0]
            usym2 = 'E'
            ugl2 = 1
            ugq2 = (uq2,usym2,ugl2)

            ugqs = (ugq1,ugq2)

        if nu == 4:
            lq = [1,0,0,0]
            lsym = 'A1'
            lgl = 1
            lgq = (lq,lsym,lgl)

            uq = [1,0,1,0]
            usym = 'F2'
            ugl = 1
            ugq = (uq,usym,ugl)

            ugqs = (ugq,)
            if j == 8 and branch == 1 and ll == 8 and ul == 10:
                ll = 10
                ul = 81

        for ugq in ugqs:
            htline = hitran.search_db(6,1,lgq,ugq,branch,j,ll=ll,ul=ul)
            if htline is None:
                continue
            break
        assert htline is not None
        htline = htline
    else:
        htline = metadata['hitran line']
    return tuple(htline)
fslines = {}
for index, (fsds, fsmd) in enumerate(zip(fsdsl,fsmdl)):
    print(index,len(fsdsl))
    if index in skipindices:
        continue
    fsmdpath = fsfolder + [fsmd]
    fsdspath = fsfolder + [fsds]
    fsmetadata = gc.get_metadata(fsmdpath)
    htline = get_htline(fsmetadata,fsds)
    created = datetime.datetime.fromisoformat(fsmetadata['_created']).timestamp()    
    fslines[htline] = (created,(fsdspath,fsmdpath))
print('fslines:')
print('-'*20)
print(
    '\n'.join(
        ds[-1] for c,(ds,md) in sorted(fslines.values())
    )
)
fclines = {}
fcindex = 0
for htline, (created,(fsdspath,fsmdpath)) in sorted(fslines.items(),key=lambda x: x[1][0]):    
    for fcds, fcmd in list(zip(fcdsl,fcmdl))[fcindex:]:
        fcindex += 1        
        fcmdpath = fcfolder + [fcmd]
        fcdspath = fcfolder + [fcds]
        fcmetadata = gc.get_metadata(fcmdpath)
        createdp = datetime.datetime.fromisoformat(fcmetadata['_created']).timestamp()
        if createdp < created:
            continue
        htlinep = get_htline(fcmetadata,fcds)        
        if htlinep != htline:
            continue                
        fclines[htlinep] = (createdp,(fcdspath,fcmdpath))
        break
    print(hitran.fmt_line(htline))
    assert htline in fclines

for htline in fslines.keys():
    print(hitran.fmt_line(htline[2:]),fclines[htline][0]-fslines[htline][0])

sanitized = {
    htline:{
        sanitize.FC:fclines[htline][1][0],
        sanitize.FS:fslines[htline][1][0]
    } for htline in fslines
}

N = 20
print(
    '\n'.join(
        '{}\t:\t{}'.format(*l)
        for l in map(
            lambda t: map(lambda s: s.ljust(N),t),
            [
                ['fs name','fc name'],
                ['-'*N] * 2,*[
                    [
                        d[key][-1] for key in (sanitize.FS,sanitize.FC)
                    ] for d in sanitized.values()
                ]
            ]
        )
    )
)

def get_bool(prompt,default):
    response = input(
        '{} ({}): '.format(
            prompt,
            '[y]/n' if default else 'y/[n]'
        )
    )
    return {'y':True,'n':False}[response.lower()[0]] if response else default

if args.autophase:
    autophase = {
        'y':True,'n':False
    }[args.autophase]
    print('autophasing?:',args.autophase)
else:
    autophase = get_bool('autophasing?',False)
if args.freq:
    freqcalib = {
        'y':True,'n':False
    }[args.freq]
    print('frequency calibrating?:',args.freq)
else:
    freqcalib = get_bool('frequency calibrating?',False)
    
sanitize.sanitize_experiment(
    pcpath,phimin,phimax,phio,
    sanitized,    
    autophase=autophase,freqcalib=freqcalib
)