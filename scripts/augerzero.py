import daqmx

with daqmx.TaskHandler(['auger energy']) as aot:
    daqmx.write_sample(aot,0)