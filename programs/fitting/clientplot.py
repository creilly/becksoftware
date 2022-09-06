from saturation import communicator
import os
from saturation import sanitize
import json
import numpy as np
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit
import hitran as ht

imagefoldertail = 'images'
popfname = 'pops.json'

parser = communicator.Parser()
config = parser.get_config()

imagefolder = os.path.join(
    config.get_outputfolder(),
    parser.get_timestamp(),
    imagefoldertail
)

factors = config.get_factors()

client = communicator.Client(parser.get_infile(),parser.get_outfile())

datad = client.get_data(factors)

client.quit()

popsd = {}

datafolder = config.get_datafolder()
datamd = sanitize.load_metadata(datafolder)

if not os.path.exists(imagefolder):
    os.makedirs(imagefolder)

Nm = 3
Nc = 4
def fit(x,dx,*a):
    return sum(
        an * (x/dx)**(2*n) for n, an in 
        enumerate(a)
    )

deltaf = 10.0 # megahertz
sigmao = 10.0 # megahertz
for lineindex, lined in datad.items():
    print('*'*20)
    print('line index: {:d}'.format(lineindex))
    print('*'*20)
    print('')
    for mode, computeds in lined.items():
        deltaomegas, powers, measureds = sanitize.load_data(lineindex,mode,datafolder).transpose()
        xs, yms, ycs = map(
            np.array,
            zip(
                *sorted(
                    zip(
                        {sanitize.FC:powers,sanitize.FS:deltaomegas/(2.*np.pi)}[mode],
                        measureds,
                        computeds
                    )
                )
            )
        )        
        # get line entry from sanitization output  
        linemd = datamd[lineindex]           
        # get data point of max excitation probability
        maxindex = ycs.argmax()
        # get computed excitation probability for tagging conditions of point of max amplitude
        maxprob = ycs[maxindex]
        # get normalized bolometer signal for point of max amplitude
        maxnormamp = yms[maxindex]
        if mode == sanitize.FS:            
            ffs, fyms, fycs = map(
                np.array,
                zip(
                    *filter(
                        lambda x: abs(x[0]) < deltaf,
                        sorted(
                            zip(
                                xs,yms,ycs                        
                            )
                        )
                    )
                )
            )
            m_ps, _ = curve_fit(fit,ffs,fyms,[sigmao,maxnormamp,-1/2*maxnormamp,*[0]*(Nm-2)])
            _, maxnormamp, *_ = m_ps
            c_ps, _ = curve_fit(fit,ffs,fycs,[sigmao,maxprob,-1/2*maxprob,*[0]*(Nc-2)])
            _, maxprob, *_ = c_ps
        # scale by normalizing factor to recover original measured bolometer signal
        maxamp = maxnormamp * linemd['scales'][str(mode)]
        # 1. divide tagging signal by tagging bolometer gain
        # 2. divide by measured chopping reference signal
        # 3. multiply by chopping reference bolometer gain
        maxratio = maxamp * linemd['sensitivity factor']
        # divide by excitation probability to get level population proxy
        pop = maxratio / maxprob
        # print sequence to log
        print(
            'm:',mode,'\t','i:',maxindex,
            ', '.join(
                [
                    '{}: {:.2e}'.format(label,num) for label, num in (
                        ('prob',maxprob),
                        ('nmap',maxnormamp),
                        ('ampl',maxamp),
                        ('rati',maxratio),
                        ('popu',pop)
                    )
                ]
            )
        )
        if mode == sanitize.FS:   
            # add to dictionary of populations
            popsd[lineindex] = pop
        # y_measureds = yms * linemd['scales'][str(mode)]
        # y_calcs = ycs / ycs.sum() * y_measureds.sum()
        plt.plot(xs,yms*ycs.sum(),'.')
        plt.plot(xs,ycs)
        if mode == sanitize.FS:
            pfs = np.linspace(min(ffs),max(ffs),100)            
            plt.plot(pfs,fit(pfs,*m_ps)*ycs.sum(),label='meas. peak fit')
            plt.plot(pfs,fit(pfs,*c_ps),label='calc. peak fit')
            plt.legend()
        plt.title(
            'line {:d} {}'.format(
                lineindex,{
                    sanitize.FC:'fluence curve',
                    sanitize.FS:'frequency scan'
                }[mode]
            ) + '\n' + 
            ht.fmt_line(linemd['hitran line']) + '\n' + 
            ', '.join(
                [
                    '{}: {:.2e}{}'.format(
                        label,num,'' if units is None else ' {}'.format(units)
                    ) for label, num, units in (
                        ('exc prob',maxprob,None),
                        ('max amp',1e3*maxamp,'mv'),
                        ('sens fact',1e-3*linemd['sensitivity factor'],'mv-1')
                    )
                ]
            )      
        )
        plt.xlabel(
            {
                sanitize.FS:'frequency offset (megahertz)',
                sanitize.FC:'laser power (watts)'
            }[mode]
        )
        plt.ylabel('excitation probability') 
        imagename = '{:03d}-{:d}.png'.format(lineindex,mode)     
        print(imagename,flush=True)
        plt.tight_layout()
        plt.savefig(
            os.path.join(
                imagefolder,
                imagename
            )
        )
        plt.cla()
with open(os.path.join(imagefolder,popfname),'w') as f:    
    json.dump(
        [ popsd[key] for key in sorted(popsd.keys()) ],
        f, indent=2
    )
    