from ctypes import *
from daqmx import *
import numpy as np
from time import time as comptime

energy_output_channel = 'auger energy output'
current_input_channel = 'auger emission input'

def load_energy_output():
    handle = create_task()
    add_global_channel(handle,energy_output_channel)
    return handle

def set_energy_output(handle,energy):
    write_sample(handle,energy)

def load_emission_input():
    handle = create_task()
    add_global_channel(handle,current_input_channel)
    return handle

def get_emission_input(handle):
    emission_current = c_double()
    daqmx(
        dll.DAQmxReadAnalogScalarF64,
        handle,
        -1,
        byref(emission_current),
        None
    )
    return emission_current.value

_dtmax = 10.000 # time between read operations (seconds)
def scan_line(emin,emax,scanrate,delay,tau,cb):

    aotask = create_task()
    add_global_channel(aotask,'auger energy output')
    write_sample(aotask,emin)

    starttime = comptime()

    samprate = 1E5
    
    aitask = create_task()

    inchans = (
            'auger lockin x input',
            'auger lockin y input',
            'auger emission input'
    )
    nchans = len(inchans)
    for chan in (
            'auger lockin x input',
            'auger lockin y input',
            'auger emission input'
    ):
        add_global_channel(aitask,chan)


    
    tasks = (aitask,aotask)
    
    cotask = create_task()
    add_global_channel(cotask,'auger start trigger')
    term = get_co_term(cotask)
    
    chunksize = int(_dtmax*samprate)
    wiggle = 0.5
    for task in tasks:
        cfg_samp_clk_timing(
            task,samprate,CONT_SAMPS,int((1+wiggle)*chunksize)
        )
        cfg_trigger(task,term)

    e = emin
    de = scanrate / samprate
    nout = 0
    N = int((emax - emin)/scanrate*samprate)

    def update_buff(nout,e,started):
        ngen = get_samps_generated(aotask) if started else 0
        dn = nout - ngen
        n = chunksize - dn
        if n:
            data = np.minimum(e + de * np.arange(n),emax)
            write_to_buff(
                aotask,
                np.minimum(e + de * np.arange(n),emax)
            )
        return nout + n, min(e + de * n,emax)
    
    dnout = min(N,chunksize)
    nout, e = update_buff(nout,e,False)

    for task in tasks:
        start_task(task)

    while comptime() - starttime < delay:
        continue
    start_task(cotask)

    nin = 0

    vprevs = None

    def decimate(data,samps,prev,offset):
        c1 = (samps-1) / samps
        c2 = 1 / samps
        decimated = []
        for datum in data:
            prev = c1 * prev + c2 * datum
            if (offset % samps) == 0:
                decimated.append(prev)
            offset += 1
            
        return decimated, prev
    
    sampstau = int(samprate*tau+1)
    m = 0
    while nin < N:
        nout, e = update_buff(nout,e,True)
        nacqd = get_samps_acquired(aitask)
        n = min(N - nin,nacqd - nin)
        if n == 0:
            continue
        data = read_buff(aitask,n)
        if vprevs is None:
            vprevs = [row[0] for row in data]
        decimateds = []
        for index, row in enumerate(data):
            decimated, prev = decimate(row,sampstau,vprevs[index],nin)
            vprevs[index] = prev
            decimateds.append(decimated)
        dm = len(decimated)
        if dm:
            cb(
                [
                    list(
                        emin
                        +
                        sampstau*de*np.arange(m,m+dm)
                    )
                ] + decimateds
            )
            m += dm
        nin += n

    for task in (aitask,aotask,cotask):
        stop_task(task)
        clear_task(task)

if __name__ == '__main__':
    from matplotlib import pyplot as plt
    from grapher import graphclient as gc
    path = gc.add_dataset(
        ['tmp'],'auger scan test',
        ('energy (eV)','lockin x (V)', 'lockin y (V)', 'beam current (uA)')
    )
    def cb(newdata):
        print('new data. e:','{:.1f}'.format(newdata[0][-1]), '/', emax)
        gc.add_data_multiline(
            path,list(zip(*newdata))
        )
        for index, row in enumerate(newdata):
            data[index].extend(row)    
    data = [[] for _ in range(4)]
    emin = 700
    emax = 1000
    scan_line(emin,emax,3.0,3.0,0.5,cb)
    for row in range(1,2):
        plt.plot(data[0],data[row],'.')
    plt.show()
