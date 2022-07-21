import laselock as ll
from os import path

rootfolder = r'Z:\Surface\chris\calibrations\laselock'

with ll.LaseLockHandler() as llh:
    vs = ll.vardump(llh)
    fname = '{}.llv'.format(input('enter name (no extension): '))
    ll.save_vars(path.join(rootfolder,fname),vs)
    print('calibration saved.')
