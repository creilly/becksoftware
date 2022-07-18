from saturation import communicator
import os
from saturation import sanitize
import json
import numpy as np
from matplotlib import pyplot as plt

imagefoldertail = 'images'
mdfname = 'metadata.json'

parser = communicator.get_parser()

parser.add_argument('-f','--factors',nargs=4,type=float)

args = parser.parse_args()

imagefolder = os.path.join(
    communicator.get_output_folder(args),
    '{}-{}'.format(communicator.get_timestamp(args),imagefoldertail)
)

factors = args.factors

client = communicator.Client(*communicator.get_pipes(args))

datad = client.get_data(factors)

try:
    config = communicator.get_config(args)
    configmd = {s:dict(config.items(s)) for s in config.sections()}
    datafolder = communicator.get_data_folder(args)
    md = {
        'factors':{
            key:value for key, value in zip(
                ('power','gamma','sigmaomega','tau'),
                factors
            )
        },
        'datafolder':datafolder
    }

    md.update(configmd)

    if not os.path.exists(imagefolder):
        os.makedirs(imagefolder)

    with open(os.path.join(imagefolder,mdfname),'w') as f:
        json.dump(md,f,indent=2)

    for lineindex, lined in datad.items():
        for mode, computeds in lined.items():
            deltaomegas, powers, measureds = sanitize.load_data(lineindex,mode,datafolder).transpose()
            xs, yms, ycs = zip(
                *sorted(
                    zip(
                        {sanitize.FC:powers,sanitize.FS:deltaomegas/(2.*np.pi)}[mode],
                        measureds,
                        computeds
                    )
                )
            )          
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
            plt.ylabel('bolometer signal (normalized)') 
            imagename = '{:03d}-{:d}.png'.format(lineindex,mode)     
            print(imagename,flush=True)
            plt.savefig(
                os.path.join(
                    imagefolder,
                    imagename
                )
            )
            plt.cla()
finally:
    client.quit()