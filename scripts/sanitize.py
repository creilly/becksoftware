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
    extras = []
    while True:
        extra = input('enter extra folder (enter to continue): ')
        if extra:
            extras.append(extra)
            continue
        break
    return [year,month,day,*extras]

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
        rawskipindicesp = args.lines
        print('line skip indices:',rawskipindicesp)        
    else:
        print(
            fmt_dir(
                [
                    ds for n, ds in enumerate(dds) if n not in skipindices
                ]
            )
        )
        rawskipindicesp = input('enter *ht lines* to skip by freq scan index (enter to continue): ')
        if not rawskipindicesp:
            break    
    skipindicesp = parse_number_list(rawskipindicesp)
    for skipindex in skipindicesp:
        root, leaf = dds[skipindex].split('-',1)
        for dsp in dds:
            rootp, leafp = dsp.split('-',1)            
            indexp = int(rootp)
            if leafp == leaf:                
                if indexp not in skipindices:
                    skipindices.append(indexp)
    if args.lines is not None:
        break

while True:
    if args.datasets is not None:
        rawskipindices = args.datasets        
        print('skip indices:',rawskipindicesp)
    else:
        print(
            fmt_dir(
                [
                    ds for n, ds in enumerate(dds) if n not in skipindices
                ]
            )
        )
        rawskipindices = input('enter *datasets* to skip by freq scan index (enter to continue): ')
    if not rawskipindices:
        break
    skipindicesp = parse_number_list(rawskipindices)
    skipindices += skipindicesp  
    if args.datasets is not None:
        break  

fsdsl, _, fsmdl = gc.get_dir(fsfolder)
fcdsl, _, fcmdl = gc.get_dir(fcfolder)

fslines = {}
for index, (fsds, fsmd) in enumerate(zip(fsdsl,fsmdl)):    
    if index in skipindices:
        continue
    fsmdpath = fsfolder + [fsmd]
    fsdspath = fsfolder + [fsds]
    fsmetadata = gc.get_metadata(fsmdpath)
    htline = tuple(fsmetadata['hitran line'])
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
        htlinep = tuple(fcmetadata['hitran line'])           
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
bools = []
for boolname, boolkey, booldef in (('autophasing','autophase',False),('frequency calibrating','freq',False)):
    arg = getattr(args,boolkey)
    if arg:
        boolval = {
            'y':True,'n':False
        }[arg]
        print('{}?:'.format(boolname),arg)
    else:
        boolval = get_bool('autophasing?',booldef)
    bools.append(boolval)
autophase, freqcalib = bools
    
sanitize.sanitize_experiment(
    pcpath,phimin,phimax,phio,
    sanitized,    
    autophase=autophase,freqcalib=freqcalib
)