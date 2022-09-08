import powercalib
from grapher import graphclient as gc
import rotationstage
import numpy as np
import datetime as dt

def get_value(prompt,format,default):
    response = input('{} [{}]: '.format(prompt,str(default)))
    if response:
        return format(response)
    else:
        return default

now = dt.datetime.now()

zeropad = lambda x: '{:02d}'.format(int(x))

year = get_value('enter year',str,str(now.year))
month = get_value('enter month',zeropad,)
month = '{:02d}'.format(int(input('enter month [{:d}]: '.format(now.month))))
day = '{:02d}'.format(int(input('enter day [{:d}]: '.format(now.day))))
extrafolders = []
while True:
    extrafolder = input('enter extra folder name #{:d}, or enter to continue: '.format(len(extrafolders) + 1))
    if extrafolder:
        extrafolders.append(extrafolder)
    else:
        break
folder = [year,month,day] + extrafolders

dsindex = int(input('enter ds index: '))

path = folder + [gc.get_dir(folder)[0][dsindex]]

phimin = float(input('enter minimum angle of fit range: '))
phimax = float(input('enter maximum angle of fit range: '))

_, ((thetamax,*_),_) = powercalib.get_fit_params(path,phimin,phimax)
thetamax = np.rad2deg(thetamax)

print('phi max: {:.2f} degrees'.format(thetamax))

showdemo = input('show demo? (y/[n]): ')
if showdemo:
    if showdemo.strip().lower()[0] == 'y':
        powercalib.run_demo(path,phimin,phimax,10)
        looksgood = input('looks good? ([y]/n): ')
        if looksgood:
            if looksgood.strip().lower()[0] == 'n':
                print('does not look good. exiting.')
                exit()

with rotationstage.RotationStageHandler() as rsh:
    print('setting angle...')
    rotationstage.set_angle(rsh,thetamax)
    print('angle set.')