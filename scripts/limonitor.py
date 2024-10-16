import lockin, argparse
from grapher import graphclient as gc
from time import sleep, time

ap = argparse.ArgumentParser()
ap.add_argument(
    '--tau','-t',help='time constant in seconds. update rate is 10 x tau',type=float,default=300e-3    
)
args = ap.parse_args()
tau = args.tau
folder = [*gc.get_day_folder(),'lockin monitor']
name = input('enter dataset name: ')
description = input('enter description: ')
interval = 10*tau

with lockin.LockinHandler() as lih:
    taup = lockin.set_time_constant(lih,tau)
    intervalp = taup * 10
    to = time()
    path = gc.add_dataset(
        folder,
        name,
        ('time elapsed (seconds)','lockin r (volts)','lockin t (degs)'),        
        {
            'description':description
        }
    )    
    print('startin lockin monitor, press ctrl-c to quit.')
    while True:
        try:
            sleep(intervalp)
            r,t = lockin.get_rt(lih)
            gc.add_data(path,(time()-to,r,t))
        except KeyboardInterrupt:
            print('keyboard interrupt received. quitting.')
            break