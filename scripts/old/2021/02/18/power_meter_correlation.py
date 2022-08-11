from grapher import graphclient as gc
from powermeter import get_power as tl_get_power
import wavemeter as wm
from time import time
br_get_power = wm.get_power
old = wm.OLD

samples = 1000
path = gc.add_dataset(gc.get_day_folder(),'pm tl fast timed',['time (s)','thorlabs power meter (watts)'])
start_time = time()
for sample in range(samples):
    gc.add_data(path,[time()-start_time,tl_get_power()])
