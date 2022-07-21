import os
from os import path
import laselock as ll

calibfolder = r'Z:\Surface\chris\calibrations\laselock'

calibfiles = {
    (i+1):f for i, f in
    enumerate(
        filter(
            lambda f: path.isfile(os.path.join(calibfolder,f)),
            os.listdir(calibfolder)
        )
    )
}

print('pick a calibration file to load:')

print(
    '\n'.join(
        '{:d}\t:\t{}'.format(i,f)
        for i, f in sorted(calibfiles.items())
    ),
    ''
)

calibfile = os.path.join(
    calibfolder,
    calibfiles[
        int(
            input('enter number: ')
        )
    ]
)

llvars = ll.load_vars(calibfile)

print('writing params to ll...')
with ll.LaseLockHandler() as llh:
    ll.write_vars(llh,llvars)
print('done!')
