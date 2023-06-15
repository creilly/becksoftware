import lockin
from grapher import graphclient as gc
from time import sleep, time

folder = [*gc.get_day_folder(),'lockin monitor']
name = input('enter dataset name: ')
description = input('enter description: ')
interval = 3.0 # seconds
tau = interval / 10

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