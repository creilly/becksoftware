from saturation import communicator
import os
from saturation import sanitize
import json
import numpy as np
from matplotlib import pyplot as plt

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

for lineindex, lined in datad.items():
    for mode, computeds in lined.items():
        deltaomegas, powers, measureds = sanitize.load_data(lineindex,mode,datafolder).transpose()
        xs, yms, ycs = map(
            np.array,
            zip(
                *sorted(
                    zip(
                        {sanitize.FC:powers,sanitize.FS:deltaomegas/(2.*np.pi)}[mode],
                        measureds*sum(computeds),
                        computeds
                    )
                )
            )
        )
        if mode == sanitize.FC:     
            linemd = datamd[lineindex]           
            maxindex = xs.argmax()
            maxprob = ycs[maxindex]
            maxamp = yms[maxindex]
            maxratio = maxamp * linemd['scales'][str(sanitize.FC)] * linemd['sensitivity factor']
            pop = maxratio / maxprob
            popsd[lineindex] = pop
        plt.plot(xs,yms,'.')
        plt.plot(xs,ycs)
        plt.title(
            'line {:d} {}'.format(
                lineindex,{
                    sanitize.FC:'fluence curve',
                    sanitize.FS:'frequency scan'
                }[mode]
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
    