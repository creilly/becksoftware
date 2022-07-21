import numpy as np
from daqmx import *
from grapher import graphclient as gc
import lockin
import topo
from time import time
from topo import topoclient as tc
import oscilloscope as scope
import powermeter as pm
import wavemeter as wm
from pyvisa.errors import VisaIOError
import fit
from matplotlib import pyplot as plt
import hitran

VMAX = 3.5 # volts
wait = 2.0 # seconds
rampdown = 5.0 # seconds
dvramp = 0.001 # volts

FREQUENCY, LOCKIN_X, LOCKIN_Y, IR_PHOTODIODE = 'frequency', 'topo lockin x', 'topo lockin y', 'ir photodiode'

TEMP_CONTROL = 'topo temperature control'
CURR_CONTROL = 'topo current control'

dfdt = -28.4486471200e3 # MHz / deg C
def scan_line(
        deltaf, # MHz scan width
        df, # MHz resolution
        fscanrate, # MHz / s
        inchans,
        cb,
        wait=wait
):
    aitask = aotask = cotask = None
    try:
        dfdt = -28.4486471200e3 # MHz / deg C

        fmin = -deltaf/2
        fmax = +deltaf/2

        print('fmin',fmin,'fmax',fmax)

        tmin = fmin / -dfdt
        tmax = fmax / -dfdt

        tscanrate = fscanrate / -dfdt

        print('tmin',tmin,'tmax',tmax)

        dtdv = max(tmax / VMAX,.002)

        print('dtdv requested:',dtdv)
        topo.set_analog_temperature_scaling_factor(dtdv)
        dtdv = topo.get_analog_temperature_scaling_factor()
        print('dtdv set:',dtdv)

        vmin = tmin / dtdv
        vmax = tmax / dtdv

        vscanrate = scanrate = tscanrate / dtdv

        print('vmin',vmin,'vmax',vmax)

        tau = df / fscanrate # software averaging time constant 

        _dtmax = 5.000 # max time between read operations (seconds)

        aitask = create_task()

        nchans = len(inchans)
        for chan in inchans:
            add_global_channel(aitask,chan)

        aotask = create_task()
        add_global_channel(aotask,'topo temperature control')
        vramp = 0
        print('ramping down...')
        while True:
            print(', '.join(map('{:.3f}'.format,(vramp,vmin))))
            vramp = max(vmin,vramp)
            write_sample(aotask,vramp)
            if vramp == vmin:
                break
            vramp -= dvramp
            
        start_time = time()

        samprate = 1E5

        tasks = (aitask,aotask)

        cotask = create_task()
        add_global_channel(cotask,'topo scan trigger')
        term = get_co_term(cotask)

        chunksize = int(_dtmax*samprate)
        wiggle = 0.5
        for task in tasks:
            cfg_samp_clk_timing(
                task,samprate,CONT_SAMPS,int((1+wiggle)*chunksize)
            )
            cfg_trigger(task,term)

        v = vmin
        dv = scanrate / samprate
        nout = 0
        N = int((vmax - vmin)/scanrate*samprate)

        def update_buff(nout,v,started):
            ngen = get_samps_generated(aotask) if started else 0
            dn = nout - ngen
            n = chunksize - dn
            if n:
                data = np.minimum(v + dv * np.arange(n),vmax)
                write_to_buff(
                    aotask,
                    np.minimum(v + dv * np.arange(n),vmax)
                )
            return nout + n, min(v + dv * n,vmax)

        dnout = min(N,chunksize)
        nout, v = update_buff(nout,v,False)

        for task in tasks:
            start_task(task)

        while not topo.get_diode_temperature_ready():
            continue
        while time() - start_time < wait:
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
            nout, v = update_buff(nout,v,True)
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
                        [label,series] for label, series in zip(
                            [FREQUENCY] + list(inchans),
                            [
                                list(
                                    dfdt * dtdv * (
                                        vmin
                                        +
                                        sampstau*dv*np.arange(m,m+dm)
                                    )
                                )
                            ] + decimateds
                        )
                    ]
                )
                m += dm
            nin += n

    finally:
        for task in (aitask,aotask,cotask):
            if task is not None:
                stop_task(task)
                clear_task(task)
        aotask = create_task()
        add_global_channel(aotask,'topo temperature control')
        vramp = vmax
        print('ramping home...')
        while True:
            print(', '.join(map('{:.3f}'.format,(vramp,0))))
            vramp = max(0.0,vramp)
            write_sample(aotask,vramp)
            if vramp == 0.0:
                break
            vramp -= dvramp
        stop_task(aotask)
        clear_task(aotask)
        
def _do_nothing(data):
    pass

def scan_and_save(
    deltaf,df,fscanrate,inchans,folder,name,
    notes=None,user_cb=_do_nothing,wait=wait
):
    with scope.ScopeHandler() as sh:
        vrms = scope.get_rms_noise(sh)
        noise_enabled = scope.get_wavesource_enabled(sh)
        
    with lockin.LockinHandler() as lia:
        lockin_frequency = lockin.get_frequency(lia)
        lockin_amplitude = lockin.get_mod_amp(lia)
        lockin_time_constant = lockin.get_time_constant(lia)
        lockin_sensitivity = lockin.get_sensitivity(lia)
        
    topo_analog_current_scaling_factor = topo.get_analog_current_scaling_factor()
    metadata = {}
    scanparams = {
        'scan rate':(fscanrate,'MHz per second'),
        'lockin frequency':(lockin_frequency,'hertz'),
        'lockin amplitude':(lockin_amplitude,'volts'),
        'lockin sensitivity':(lockin_sensitivity,'volts'),
        'lockin time constant':(lockin_time_constant,'seconds'),
        'topo analog current scaling factor':(topo_analog_current_scaling_factor,'millamps per volt'),
        'current noise':(vrms,'volts rms'),
        'noise enabled':noise_enabled
    }
    metadata['scan parameters'] = scanparams
    metadata['notes'] = notes
    path = gc.add_dataset(
        folder,name,
        [
            '{} ({})'.format(name,units) for name, units in zip(
                ['laser frequency'] + list(inchans),
                ['MHz'] + ['volts']*len(inchans)
            )
        ],
        metadata=metadata
    )
    def cb(data):            
        for label, series in data:
            if label in (LOCKIN_X,LOCKIN_Y):
                for n in range(len(series)):
                    series[n] *= lockin_sensitivity / 10.0
        gc.add_data_multiline(
            path,
            list(zip(*list(zip(*data))[1]))
        )
        user_cb(data)

    scan_line(
        deltaf, # MHz scan width
        df, # MHz resolution
        fscanrate, # MHz / s
        inchans,
        cb,
        wait=wait
    )

# aux chans: in addition to LOCKIN_X and LOCKIN_Y
def recenter_series(
    deltaf,df,fscanrate,outer_cb,auxchans=[],
    inner_cb=_do_nothing,wait=wait,der=False
):
    inchans = [LOCKIN_X,LOCKIN_Y]+auxchans
    def get_cb(totals):
        def cb(data):
            transposed = list(zip(*data))[1]
            for total, row in zip(totals,transposed):
                total.extend(row)
            inner_cb(data)
        return cb
    while True:
        cont, folder, name, notes = outer_cb()
        if not cont:
            break
        data = []
        while len(data) < 1 + len(inchans):
            data.append([])
        scan_and_save(
            deltaf,df,fscanrate,
            inchans,
            folder,
            name,
            notes = notes,
            user_cb = get_cb(data)
        )
        fs, xs, ys = map(np.array,data[:3])
        phase = fit.auto_phase(xs,ys,0.01)
        xps = fit.rephase(xs,ys,phase)
        if der:
            xps = np.cumsum(xps)
        dfmax = fs[np.abs(xps).argmax()]
        print('dfmax: ',dfmax)
        dtmax = dfmax/dfdt
        print('dtmax: ',dtmax)
        to = topo.get_diode_set_temperature()
        print('to: ',to)
        tp = to + dtmax
        print('setting to: ',tp)
        topo.set_diode_temperature(tp)

def get_lock(wnum,n,epsilon_wnum,dt):
    print('starting get lock with:')
    print('n',n)
    print('epsilon_wnum',epsilon_wnum)
    print('dt',dt)
    wact = tc.get_wavenumber_act()
    starttime = None
    while True:
        dwnum = np.abs(wact - wnum)
        print('delta wnum:','{:.5f}'.format(dwnum))
        if dwnum < epsilon_wnum:
            if starttime is None:
                starttime = time()
            else:
                tot = time() - starttime
                print('time on target: {:.1f}'.format(tot))
                if tot > dt:
                    break
        else:
            if starttime is not None:
                starttime = None
        newwact = tc.get_wavenumber_act()
        wact = wact * n / (n+1) + newwact / (n+1)

def set_wnum(wnum):
    _set_topo(wnum,tc.set_wavenumber,wnum)

def set_line(branch,j,A,dw):
    wnum = hitran.get_branch(branch)[j][A]
    _set_topo(wnum+dw,tc.set_line,branch,j,A,dw)

def _set_topo(wnum,f,*args):
    with scope.ScopeHandler() as sh:
        ws_enabled = scope.get_wavesource_enabled(sh)
        scope.set_wavesource_enabled(sh,False)
            
    cc_enabled = topo.get_analog_current_enabled()
    topo.set_analog_current_enabled(False)
    
    swnum = '{:.5f}'.format(wnum)
    print('setting etalon and motor for wnum {}'.format(swnum))
    f(*args)

    tc.set_damping(5.0)
    tc.set_locking(True)
    
    n = 3
    epsilon_wnum = 0.005
    dt = 5.0
    
    get_lock(wnum,n,epsilon_wnum,dt)

    tc.set_damping(10.0)

    n = 3
    epsilon_wnum = 0.0005
    dt = 10.0

    get_lock(wnum,n,epsilon_wnum,dt)

    tc.set_locking(False)

    topo.set_analog_current_enabled(cc_enabled)

    with scope.ScopeHandler() as sh:
        vrms = scope.set_wavesource_enabled(sh,ws_enabled)

def get_wnum_and_power(M,N):
    with wm.WavemeterHandler() as wmh, pm.PMHandler() as pmh:
        n = 0
        wavg = 0
        wvar = 0
        pavg = 0
        while n < M + N:
            n += 1
            while True:
                try:
                    wnew = wm.get_wavenumber(wmh)
                    break
                except VisaIOError:
                    continue
            if n > M:
                pnew = pm.get_power(pmh)
                wavg += wnew
                wvar += wnew**2
                pavg += pnew
    wavg /= N
    wvar /= N
    pavg /= N
    wstd2 = wvar - wavg**2
    if wstd2 < 0:
        wstd2 = 0
    wstd = np.sqrt(wstd2)
    return wavg, wstd, pavg

if __name__ == '__main__':
    wnum = 3028.7478
    set_wnum(wnum)
    deltaf = 100.0 # MHz
    df = 1.0 # MHz
    fscanrate = 1.0 # MHz / s
    def user_cb(data):
        freqs = data[0][1]
        avgfreq = sum(freqs)/len(freqs)
        print(
            '\t'.join(
                (
                    'freq:',
                    '{:.2f}'.format(-deltaf/2),
                    '<--',
                    '{:.2f}'.format(avgfreq),
                    '-->'
                    '{:.2f}'.format(+deltaf/2)
                )
            )
        )
    scan_and_save(
        deltaf,df,fscanrate,
        [LOCKIN_X,LOCKIN_Y],
        gc.get_day_folder() + ['tmp-test'],
        'test spectrum',
        notes = {'text':'some test notes','list':[1,2,3]},
        user_cb = user_cb
    )
