import beckhttpserver as bhs
import pwm
import daqmx as d
import numpy as np
from scipy.optimize import curve_fit
import struct
import base64
import fit
import math
import topo
from time import time

PORT = 8999

FM = False
# heater parameters

hchan = 'transfer cavity heater'
hres = 5000
hvmax = 5.0
hvo = 0.0
hvsafe = 5.0

# scan parameters

deltat = 0.015 # seconds
deltav = 8.0 # volts
epsilon = 0.1 # v / v
samplingrate = 200e3 # 200e3 # samples per second
buffersize = 100 # in reps
decimation = 3

# test
modfreq = 511 # hertz

# fit configuration

history = 50
dfdv = 100.0 # MHz / volt (transfer cavity piezo)

# lock parameters

dvdf = -1.0 / 1.0e3 # volt (thorlabs cavity piezo) / MHz

def generate_waveform(deltav,epsilon,deltat,samplingrate):
    dv = epsilon * deltav
    freq = ( 1 - 2 * epsilon ) / (
        2 * np.pi * deltat * np.sqrt( epsilon - epsilon ** 2 )
    )
    dt = 1 / ( 2 * np.pi * freq ) * np.arccos( 1 - 2 * epsilon )
    ddt = 1 / samplingrate
    vo = dv
    v = vo
    scanvs = []
    t = 0
    while t < deltat:
        scanvs.append(v)
        v += deltav * ( 1 - 2 * epsilon ) / deltat * ddt
        t += ddt
    returnvs = []
    t = -dt
    while t < 1 / freq / 2 + dt:
        returnvs.append(
            deltav / 2 * (
                1 +
                np.cos(
                    2 * np.pi * freq * t
                )
            )
        )
        t += ddt
    return scanvs, returnvs

INPUT, OUTPUT = 0, 1
class Scanner:
    def __init__(self,ao,ai,scanvs,returnvs,samplingrate,triggerchannel):
        scansamples = len(scanvs)
        returnsamples = len(returnvs)
        samples = scansamples + returnsamples        
        d.cfg_samp_clk_timing(
            ao,samplingrate,d.CONT_SAMPS,samples,d.get_samp_clk_term(ai)
        )
        if FM:
            d.cfg_samp_clk_timing(
                ai,samplingrate,d.FINITE_SAMPS,samples,d.ONBOARD_CLK
            )
            d.set_buffer_size(ai,buffersize*samples)            
            d.cfg_trigger(
                ai,triggerchannel
            )
            d.set_retriggerable(
                ai,True
            )    
        else:
            d.cfg_samp_clk_timing(
                ai,samplingrate,d.CONT_SAMPS,buffersize*samples,d.ONBOARD_CLK
            )
        d.set_regeneration_mode(ao,True)            
        d.write_to_buff(
            ao,scanvs + returnvs
        )
        self.ao = ao
        self.ai = ai
        self.samples = samples
        self.scansamples = scansamples
        self.scanning = False
        self.index = 0

    def set_scanning(self,scanning):
        if scanning != self.scanning:
            for task in (self.ao,self.ai):
                if scanning:
                    self.index = 0                    
                    d.start_task(task)
                else:
                    try:
                        d.stop_task(task)
                    except d.DAQmxError as de:
                        print('stop exception encountered')
                        if de.code != 200010:
                            print('raising stop exception')
                            raise
        self.scanning = scanning        

    def get_scanning(self):
        return self.scanning

    def acquire_scan(self):
        if self.scanning:            
            scan = {
                chan:l[:self.scansamples] for chan,l in zip(
                    inputchannels,
                    d.read_buff(self.ai,self.samples)
                )
            }
            self.index += 1
            return scan

    def get_index(self):
        return self.index

Vo = deltav / 2
def distort_v(v,vp,vpp):    
    return Vo + 1.0 * (v - Vo) + vp * (v - Vo)**2 + vpp * (v - Vo)**3

def transmission(v,vmax,vmin,deltav,sigmav,vp,vpp,muv,df=0,phif=0):    
    v = distort_v(v,vp,vpp)
    muv = muv + df / dfdv * np.sin(
        2 * np.pi * modfreq / samplingrate * np.arange(len(v)) - np.deg2rad(phif)
    )
    b = 1/np.sin(np.pi/2*sigmav/deltav)**2 - 2
    a = ( 1 + 1 / b ) * ( vmax - vmin )
    c = vmin - a / ( 1 + b )
    return a / ( 1 + b * np.sin(np.pi * ( v - muv ) / deltav)**2 ) + c

IR, HENE = 'ir', 'hene'
inputchannels = (HENE,IR)

VMAX, VMIN, DELTAV, SIGMAV, VP, VPP, MUV, DF, PHIF  = 'vmax', 'vmin', 'deltav', 'sigmav', 'vp', 'vpp', 'muv', 'df', 'phif'

fitparamindices = fpis = (VMAX, VMIN, DELTAV, SIGMAV, VP, VPP, MUV, DF, PHIF)

initial_guesses = {
    IR:{
        VMAX:      +5.00000e-01, # +1.360e-01,
        VMIN:      +5.55663e-03, # +7.584e-03,
        DELTAV:    +2.84517e+00, # +2.777e+00,
        SIGMAV:    +4.43556e-01, # +4.061e-01,
        VP:        +2.59030e-02, # +2.69506e-02, # +2.64743369e-02,
        VPP:       -1.11975e-03, # -5.79459180e-04,
        DF:        -7.00000e-01,
        PHIF:      -3.15000e+02
    },
    HENE:{
        VMAX:      +1.50000e-01, # +8.25384e-02, # +6.47524266e-02,
        VMIN:      -1.15319e-02, # -1.20379796e-02,
        DELTAV:    +5.46350e-01, # +5.33988863e-01,
        SIGMAV:    +1.24592e-01, # +1.15531599e-01,
        VP:        +2.59030e-02, # +2.69506e-02, # +2.64743369e-02,
        VPP:       -1.11975e-03, # -5.79459180e-04,
        DF:        +0.00000e+00,
        PHIF:      +0.00000e+00
    }        
}

mufracs = {
    HENE : (0.35,0.65),
    IR   : (0.30,0.70)
}

fitfracs = {
    HENE : (0.0,1.0), # (0.10,0.90),
    IR   : (0.0,1.0) # (0.10,0.90)
}

class _Fitter:
    def __init__(self,mode):
        self.guess = None
        self.mode = mode
        self.x = np.array(scanvs)
        self.corrections = None
    

                 

class Fitter:
    def __init__(self,mode):
        self.guess = None
        self.mode = mode
        self.x = np.array(scanvs)
        self.corrections = None

    def transmission(
            self,x,vmax,vmin,deltav,sigmav,muv,*fparams
    ):
        return transmission(
            x,vmax,vmin,deltav,sigmav,*self.corrections,muv,*fparams
        )

    def fit(self,y):
        samps = scansamples
        x = self.x
        mode = self.mode
        if self.guess is None:
            musampmin, musampmax = musamps[mode]            
            musamp = musampmin + np.array(y[musampmin:musampmax]).argmax()
            muvo = x[musamp]            
            guess = [
                initial_guesses[mode][fpindex]
                for fpindex in fitparamindices[:fitparamindices.index(MUV)]
            ] + [muvo]
            if self.mode == IR:
                guess.extend(
                    initial_guesses[IR][key]                        
                    for key in fitparamindices[fitparamindices.index(MUV)+1:]
                )            
            if CO2 and self.mode == IR:
                vmax = y.max()
                vmin = y.min()
                deltav = initial_guesses[IR][DELTAV] * 3000 / 3600
                sigmav = deltav / 2
                for key, value in zip(
                    (VMAX,VMIN,DELTAV,SIGMAV),
                    (vmax,vmin,deltav,sigmav)
                ):
                    guess[fpis.index(key)] = value
        else:
            guess = self.guess        
        fitsampmin, fitsampmax = fitsamps[mode]
        fitx = x[fitsampmin:fitsampmax]
        fity = y[fitsampmin:fitsampmax]        
        try:
            if self.corrections is None:                
                params, cov = curve_fit(
                    transmission,
                    fitx,fity,
                    guess
                )
                vmax, vmin, deltav, sigmav, vp, vpp, muv, *fparams = params
                if len(fparams) == 0:
                    fparams = (0.,0.)
                params = vmax, vmin, deltav, sigmav, vp, vpp, muv, *fparams
            else:
                vmax, vmin, deltav, sigmav, vp, vpp, muv, *fparams = guess
                guess = (vmax, vmin, deltav, sigmav, muv, *fparams)                
                params, cov = curve_fit(
                    self.transmission,
                    fitx,fity,
                    guess                    
                )
                vmax, vmin, deltav, sigmav, muv, *fparams = params                
                if len(fparams) == 0:
                    fparams = (0.,0.)
                params = vmax, vmin, deltav, sigmav, *self.corrections, muv, *fparams            
            if math.nan in params:
                return None
        except RuntimeError:
            return None
        self.guess = params[:len(params)-{IR:0,HENE:2}[self.mode]]
        return {
            fpindex:param for fpindex, param in zip(fitparamindices,params)
        }

    def reset(self):
        self.guess = None

    def set_corrections(self,vp,vpp):
        self.corrections = (vp,vpp)

def encode_scan(scan):
    return base64.b64encode(
        struct.pack(
            '{:d}f'.format(len(scan)),
            *scan
        )
    ).decode()

damping = 5.0
pmin = 0.5
pmax = 3.5
class Locker:
    def __init__(self,topohandle):
        self.topohandle = topohandle
        self.setpoint = 0.0
        self.vo = self.get_ar().read_blocking()
        self.request_piezo_voltage()
        self.deltavmax = 0.01
        self.deltav = 0.0
        self.starttime = time()

    def request_piezo_voltage(self):
        self.ar = self.get_ar()
        self.waiting = True

    def get_ar(self):
        return self.topohandle.get_output(topo.A)

    def check_ar(self):
        f, vo = self.ar.read()
        if f:
            if self.waiting:
                self.vo = vo
                self.waiting = False
        return f
    
    def get_setpoint(self):
        return self.setpoint

    def set_setpoint(self,setpoint):
        self.setpoint = setpoint

    def update_lock(self,deltaf):
        errorf = deltaf - self.setpoint
        self.deltav += -(dvdf * errorf) / damping
        self.deltav = max(
            -self.deltavmax,
            min(
                self.deltav,
                self.deltavmax
            )
        )
        if self.check_ar():
            vp = self.vo + self.deltav
            self.set_piezo_voltage(vp)
            self.deltav = 0.0
            self.vo = vp

    def get_output(self):
        return self.vo

    def set_piezo_voltage(self,voltage):
        if voltage < pmin or voltage > pmax:            
            raise PiezoLimitError
        self.topohandle.set_output(topo.A,min(max(pmin,voltage),pmax))
class PiezoLimitError(Exception): pass
FULL, DECIMATED = 0, 1
HENEFITERROR, IRFITERROR = 0, 1
SCANINDEX, DELTAF = '0', '1'

NO_HEATER = 1347
def check_heater(foo):
    def bar(self,*args,**kwargs):
        if self.heater is None:
            raise bhs.BeckError('heater disabled',NO_HEATER)
        else:
            return foo(self,*args,**kwargs)
    return bar
class FrequencyMeter:
    def __init__(self,ci):
        self.ci = ci
        self.samples = d.get_samps_per_channel(ci)

    def get_frequency(self):
        freqs, nfreqs = d.read_counter_f64(self.ci,self.samples,blocking=False)
        if nfreqs:
            return np.average(freqs)
        else:
            return None
class TransferCavityApp(bhs.BeckApp):
    def __init__(self,scanner,fitters,locker,heater=None,freqmeter=None):
        self.fitting = {chan:False for chan in inputchannels}
        self.params = {            
            chan:None for chan in inputchannels
        }
        self.freqmeter = freqmeter
        self.heater = heater
        self.scanner = scanner
        self.fitters = fitters
        self.locker = locker
        self.scans = {
            chan:None for chan in inputchannels
        }
        self.errors = set()
        self.samples = []
        self.zeroing = False
        self.locking = False
        self.setpoint = 0.0
        self.offset = 0.0
        self.error = False

    def loop(self):
        if FM:
            freq = self.freqmeter.get_frequency()
            if freq is not None:
                global modfreq 
                modfreq = freq                
        if self.get_scanning():
            index = self.get_scan_index()
            muvs = {}
            self.scans = self.scanner.acquire_scan()
            for channel in inputchannels:
                if self.fitting[channel]:
                    params = self.fitters[channel].fit(
                        np.array(self.scans[channel])
                    )
                    if params is None:
                        self.errors.add(
                            {
                                HENE:HENEFITERROR,
                                IR:IRFITERROR
                            }[channel]
                        )
                        self.set_fitting(channel,False)
                        muvs[channel] = None
                    else:                        
                        muvs[channel] = distort_v(params[MUV],params[VP],params[VPP])
                        if channel is HENE:
                            self.fitters[IR].set_corrections(
                                params[VP],params[VPP]
                            )
                else:
                    params = None
                    muvs[channel] = None                
                self.params[channel] = params
            if None in muvs.values():
                deltaf = None
            else:
                deltav = muvs[IR]-muvs[HENE]
                if self.zeroing:
                    self.offset = deltav
                    self.zeroing = False                    
                deltav -= self.offset
                deltaf = dfdv * deltav
                if self.get_locking():
                    try:
                        self.locker.update_lock(deltaf)
                    except PiezoLimitError:
                        self.error = True
                        self.set_locking(False)
            if not self.get_locking():
                if self.locker.check_ar():
                    self.locker.request_piezo_voltage()
            self.samples.insert(
                0,{
                    SCANINDEX:index,
                    DELTAF:deltaf
                }
            )
            if len(self.samples) > history:
                self.samples.pop()

    @bhs.command('get error')
    def get_error(self):
        return self.error
    
    @bhs.command('clear error')
    def clear_error(self):
        self.error = False

    @bhs.command('get lock output')
    def get_lock_output(self):
        return self.locker.get_output()

    @bhs.command('get setpoint')
    def get_setpoint(self):
        return self.locker.get_setpoint()

    @bhs.command('set setpoint')
    def set_setpoint(self,setpoint):
        self.locker.set_setpoint(setpoint)

    @bhs.command('get locking')
    def get_locking(self):
        return self.locking

    @bhs.command('set locking')
    def set_locking(self,locking):
        self.locking = locking
        if not locking:
            self.locker.request_piezo_voltage()

    @bhs.command('get offset')    
    def get_offset(self):
        return self.offset

    @bhs.command('set offset')
    def set_offset(self,offset):
        self.offset = offset

    @bhs.command('zero offset')
    def zero_offset(self):
        self.zeroing = True

    # returns all errors signals with scan indices
    # larger than :index:
    @bhs.command('get samples')
    def get_samples(self,maxindex):
        n = 0
        samples = []
        while (
            n < len(self.samples)
            and
            self.samples[n][SCANINDEX] > maxindex            
        ):
            samples.insert(
                0,self.samples[n]
            )
            n += 1
        return samples

    @bhs.command('get errors')
    def get_errors(self):
        return list(self.errors)

    @bhs.command('get scanning')
    def get_scanning(self):        
        return self.scanner.get_scanning()

    @bhs.command('set scanning')
    def set_scanning(self,scanning):        
        for channel in inputchannels:
            self.reset_fitting(channel)
        self.samples = []
        self.offset = 0.0
        return self.scanner.set_scanning(scanning)

    @bhs.command('get scan index')
    def get_scan_index(self):
        return self.scanner.get_index()

    def _get_scan(self,size):
        scan = {}
        for channel in inputchannels:
            data = self.scans[channel]
            if data is not None:
                if size is DECIMATED:                    
                    data = fit.decimate(data,decimation)                    
                data = encode_scan(data)
            scan[channel] = (
                data,
                self.params[channel]
            )
        return scan

    @bhs.command('get scan')
    def get_scan(self):
        return self._get_scan(FULL)

    @bhs.command('get scan decimated')
    def get_scan_dec(self):
        return self._get_scan(DECIMATED)

    @bhs.command('get x')
    def get_x(self):
        return encode_scan(scanvs)

    @bhs.command('get x decimated')
    def get_x_dec(self):
        return encode_scan(scanvsdec)

    @bhs.command('get fitting')
    def get_fitting(self,channel):
        return self.fitting[channel]

    @bhs.command('set fitting')
    def set_fitting(self,channel,fitting):        
        if fitting:
            self.fitters[channel].reset()
        self.fitting[channel] = fitting

    @bhs.command('reset fitting')
    def reset_fitting(self,channel):
        self.fitters[channel].reset()

    @bhs.command('get fit parameters')
    def get_fit_parameters(self,channel):
        return self.params[channel]

    @bhs.command('get heating')
    @check_heater
    def get_heating(self):
        return self.heater.get_running()

    @bhs.command('set heating')
    @check_heater
    def set_heating(self,heating):
        self.heater.set_running(heating)

    @bhs.command('set heater voltage')
    @check_heater
    def set_heater_voltage(self,voltage):
        self.heater.set_voltage(voltage)

    @bhs.command('get heater voltage')
    @check_heater
    def get_heater_voltage(self):
        return self.heater.get_voltage()

    @bhs.command('get center voltage')
    def get_center_voltage(self,channel):
        if self.params[channel]:
            return self.params[channel][MUV]
        return None
    
    @bhs.command('get modulation frequency')
    def get_modulation_frequency(self):
        return modfreq if FM else -1.0

scanvs, returnvs = generate_waveform(deltav,epsilon,deltat,samplingrate)
scansamples = len(scanvs)
scanvsdec = fit.decimate(scanvs,decimation)

musamps = {
    chan:[
        int(round(scansamples*mufrac))
        for mufrac in t
    ] for chan, t in mufracs.items()
}
fitsamps = {
    chan:[
        int(round(scansamples*fitfrac))
        for fitfrac in t
    ] for chan, t in fitfracs.items()
}
METHANE, CARBON_DIOXIDE = 'ch4', 'co2'
CO2 = False
if __name__ == '__main__':
    import os
    import argparse
    ap = argparse.ArgumentParser()
    
    ap.add_argument('--molecule','-m',choices=(METHANE,CARBON_DIOXIDE),default=METHANE)
    mol = ap.parse_args().molecule
    CO2 = mol == CARBON_DIOXIDE        

    inputchannelnames = {
        HENE:'transfer cavity hene',
        IR:{True:'transfer cavity ir co2',False:'transfer cavity ir'}[CO2]
    }
    with (
            # pwm.PWM(hchan,hres,hvmax,hvo,hvsafe) as heater,
            d.TaskHandler(
                [inputchannelnames[channel] for channel in inputchannels]
            ) as ai,
            d.TaskHandler(['transfer cavity piezo']) as ao,            
            d.TaskHandler('transfer cavity frequency task',global_task=True) as ci
    ):
        heater = None        
        freqmeter = FrequencyMeter(ci) if FM else None        
        locker = Locker(topo.AsyncInstructionClient())
        scanner = Scanner(ao,ai,scanvs,returnvs,samplingrate,d.get_ci_freq_term(ci))
        fitters = {
            channel:Fitter(channel) for channel in inputchannels
        }
        print('now serving.')
        bhs.run_beck_server(PORT,os.path.dirname(__file__),TransferCavityApp,scanner,fitters,locker,heater,freqmeter,_debug=False)
