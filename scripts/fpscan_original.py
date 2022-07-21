import daqmx as d
from matplotlib import pyplot as plt
import numpy as np
import piezo
import laselock as ll
from time import sleep
import wavemeter as wm

po = 5.0 # volts

v_th_upper = 20.0e-3 # volts
v_th_lower = 0.01e-3 # volts

tau_fast = 1.0e-3 # ms
tau_slow = 10.e-3 # ms
n_peak = 15 # points per peak on fast scan
df_peak = 30 # MHz

dfdt_fast = -df_peak / n_peak / tau_fast
dfdt_slow = -dfdt_fast*tau_fast/tau_slow

peak_fraction = 0.50 # 0.75 # 0.5

sampling_rate = 50e3 # samples per second

df_fast = dfdt_fast / sampling_rate
df_slow = dfdt_slow / sampling_rate

n_fast = tau_fast * sampling_rate
n_slow = tau_slow * sampling_rate

deltat = 0.015 # response time
deltasamples = int(deltat * sampling_rate) # samples per update

fudge = 10.0
buffersamples = int(fudge*deltasamples)

wait = 0.010 # seconds

INPUT, OUTPUT = 0, 1

reg = ll.A

deltafmax = 3e3 # MHz
class SampGen:
    def __init__(self,fo,df):
        self.n = 0
        self.fo = fo
        self.df = df

    def generate_samples(self,N):
        samples = self.fo + self.df*(self.n + np.arange(N))
        self.n += N
        return samples

    def get_f(self):
        return self.get_sample(self.n)

    def get_sample(self,n):
        return self.fo + n*self.df

def update_ao(ao,sg,n):
    if n:
        try:
            d.write_to_buff(ao,sg.generate_samples(n))
            return True
        except d.DAQmxError as err:
            print('error with daqmx!',err)
            return False

class FastScanner:
    def __init__(self):
        self.vmax = None
        self.vmin = None
        self.triggered = None

    def cb(self,v):
        if v < v_th_lower:
            if self.triggered is True:
                print('fast scan done!')
                print(
                    'vmin','{:.3f} volts'.format(self.vmin),
                    'vmax','{:.3f} volts'.format(self.vmax)
                )
                vth = self.vmin + peak_fraction * (self.vmax-self.vmin)
                return True, vth
            if self.triggered is None:
                self.triggered = False
        if v > v_th_upper:
            if self.triggered is False:
                print('fast scan triggered!')
                self.triggered = True
        if self.triggered is not None:
            if self.vmin is None:
                self.vmin = v
            if v < self.vmin:
                self.vmin = v
            if self.vmax is None:
                self.vmax = v
            if v > self.vmax:
                self.vmax = v
        return False, None        

def fast_scan():
    scanner = FastScanner()
    return _scan(0.0,df_fast,n_fast,scanner.cb)

class SlowScanner:
    def __init__(self,vth):
        self.vth = vth

    def cb(self,v):
        if v > self.vth:
            print('found fringe side!')
            return True, None
        return False, None            

def slow_scan(fo,vth):
    scanner = SlowScanner(vth)
    return _scan(fo,df_slow,n_slow,scanner.cb)

def set_to_fringe_side():
    fp, vth = fast_scan()
    if fp is None:
        print('error during fast piezo scan!')
        return None, None
    fp, _ = slow_scan(fp,vth)
    if fp is None:
        print('error during slow piezo scan!')
        return None, None
    return fp, vth

def _scan(fo,df,navg,cb):
    FAST, SLOW = 0, 1
    with (
            d.TaskHandler(['fabry perot photodiode','ir photodiode']) as ai,
            d.TaskHandler(['fabry perot control']) as ao
    ):
        sg = SampGen(fo,df)
        for mode, task in ((OUTPUT,ao),(INPUT,ai)):
            d.cfg_samp_clk_timing(
                task,sampling_rate,d.CONT_SAMPS,buffersamples,
                {
                    OUTPUT:d.ONBOARD_CLK,
                    INPUT:d.get_samp_clk_term(ao)
                }[mode]
            )
        d.set_regeneration_mode(ao,False)
        success = update_ao(ao,sg,deltasamples)
        if not success:
            print('error during ao update')
            return None, None
        d.start_task(ai)
        d.start_task(ao)
        n_chans = 2
        vavg = None
        n = 0
        while True:
            if abs(sg.get_f()) > deltafmax:
                print('piezo scan range exceeded! are detectors getting signal?')
                return None, None
            try:
                fps, irs = d.read_all(ai,int(1e5),n_chans)
            except d.DAQmxError as err:
                print('during daqmx read!',err)
                return None, None
            n_read = len(fps)
            if not n_read:
                continue
            success = update_ao(ao,sg,n_read)
            if not success:
                print('error during ao update')
                return None, None
            for fppd, irpd in zip(fps,irs):
                v = fppd / irpd
                if vavg is None:
                    vavg = v
                vavg = vavg * (navg-1)/navg + v * 1 / navg
                if n > navg:
                    done, data = cb(vavg)
                    if done:
                        print('scan done!')
                        for handle, label in ((ao,'ao'),(ai,'ai')):
                            try:
                                d.stop_task(handle)
                            except d.DAQmxError as err:
                                print('error during {} task stop:'.format(label),err)
                                return None, None
                        fp = sg.get_sample(d.get_samps_generated(ao))
                        return fp, data
                n += 1

dtfppd = 0.100 # seconds
fppdmin = 0.010 # volts
smoothing = 2.5
dfmax = 1.0 # MHz
dtdfmax = 0.01 # seconds
dwmax = 0.0025
# returns pair of values
#     0: data
#         data returned by callback
#     1: wnum
#         most recently measured wavenumber
#         NOTE!
#             if function errs out, wnum
#             is set to None
def stepper(wmh,wo,cb):
    with d.TaskHandler(['fabry perot photodiode']) as ai:
        buffersamples = int(sampling_rate*dtfppd)
        d.cfg_samp_clk_timing(ai,sampling_rate,d.FINITE_SAMPS,buffersamples)
        while True:
            d.start_task(ai)
            w = wm.get_wavenumber(wmh)
            dw = w-wo
            if abs(dw) > dwmax:
                print('dw ({:.4f} cm-1) above threshold! mode hop?'.format(dw))
                return None, None
            data, result, msgs = cb(w)
            if result is None:
                print('error in handler')
                return None, None
            if result:
                print('stepping successful!')
                return data, w
            print(
                ' | '.join(
                    [
                        '{} : {}'.format(
                            label, num
                        ) for label, num in zip(
                            (
                                'w','dw'
                            ),[
                                s.rjust(15) for s in [
                                    '{:.5f} cm-1'.format(wnum)
                                    for wnum in
                                    (w,dw)
                                ] 
                            ]
                        )
                    ] + msgs
                )
            )
            wo = w
            d.task_wait(ai)
            fppds, = d.read_buff(ai,buffersamples)
            d.stop_task(ai)
            fppdavg = sum(fppds)/len(fppds)
            if fppdavg < fppdmin:
                print('fppd below threshold! lost lock?')
                return None, None

smoothing = 2.5
epsilon_f = 10.0 # MHz
class Relocker:
    def __init__(self,fo,w_target,ao):
        self.f = fo
        self.w_target = w_target
        self.epsilon_f = epsilon_f
        self.smoothing = smoothing
        self.ao = ao

    def cb(self,w):
        dfdw = 30e3
        deltaw_target = w-self.w_target
        deltaf_target = dfdw*deltaw_target
        if abs(deltaf_target) < epsilon_f:
            print('relock completed!')
            return self.f, True, []
        deltaf = -deltaf_target / smoothing
        while True:
            df = (
                dfmax*{True:+1,False:-1}[deltaf > 0]
            ) if abs(deltaf) > dfmax else deltaf                
            self.f += df
            d.write_sample(self.ao,self.f)
            deltaf -= df
            if deltaf == 0:
                break
            sleep(dtdfmax)
        return None, False, [
            '{} : {:.2f} MHz'.format(label,freq)
            for label,freq in zip(
                ('f','ep f','df targ'),   
                (self.f,epsilon_f,deltaf_target)
            )
        ]

FORWARDS, BACKWARDS = +1, -1
class Scanner:
    def __init__(self,fo,df,w,ao,cb,direction):
        self.fo = fo
        self.f = fo
        self.df = df
        self.w = w
        self.ao = ao
        self._cb = cb
        self.direction = direction

    def cb(self,w):
        if {
                FORWARDS:w>self.w,
                BACKWARDS:w<self.w
        }[self.direction]:        
            print('scan done!')
            return None, True, []
        error, msgs = self._cb(self.f-self.fo,w)
        self.f += self.direction*self.df
        d.write_sample(self.ao,self.f)
        if error:
            print('error in scan cb!')
            return None, None, []
        return None, False, [
            '{} : {} cm-1'.format(
                'w tar','{:.5f}'.format(self.w).rjust(11)
            )
        ] + [
            '{} : {} MHz'.format(
                label,'{:.2f}'.format(freq).rjust(10)
            ) for label, freq in zip(
                ('f','delta f'),
                (self.f,self.f-self.fo)
            )
        ] + msgs

def data_scan(wmh,wo,wp,fo,df,cb):
    with d.TaskHandler(['fabry perot control']) as ao:
        scanner = Scanner(
            fo,df,wp,ao,cb,
            {
                True:FORWARDS,
                False:BACKWARDS
            }[wp > wo]
        )
        return stepper(
            wmh,wo,scanner.cb
        )
    
def relock(wmh,w_target,fo):
    with d.TaskHandler(['fabry perot control']) as ao:
        relocker = Relocker(fo,w_target,ao)
        return stepper(
            wmh,w_target,relocker.cb
        )

def scan_piezo(fo,deltaf,deltat):
    buffersamples = 2*int(deltat*sampling_rate/2)
    scan_data = fo + deltaf * np.sin(2*np.pi*np.arange(buffersamples)/buffersamples)
    sync_data = 5.0 * (np.arange(buffersamples) // (buffersamples//2))
    try:
        with d.TaskHandler(['fabry perot control','fabry perot control sync']) as ao:
            d.cfg_samp_clk_timing(
                ao,sampling_rate,d.CONT_SAMPS,buffersamples
            )
            d.write_to_buff(ao,scan_data,sync_data)
            d.start_task(ao)
            input('press enter to quit: ')
    finally:
        with d.TaskHandler(['fabry perot control']) as ao:
            d.write_sample(ao,fo)

def start_locking(vth):
    with ll.LaseLockHandler() as llh:
        ll.set_reg_setpoint(llh,ll.A,vth)
        ll.set_reg_on_off(llh,ll.A,True)

def pre_scan():
    with ll.LaseLockHandler() as llh:
        ll.set_reg_on_off(llh,reg,False)
    with piezo.PiezoDriverHandler() as pdh:
        piezo.set_piezo_voltage(pdh,po)
    with d.TaskHandler(['fabry perot control']) as ao:
        d.write_sample(ao,0.0)

def post_scan():
    with ll.LaseLockHandler() as llh:
        ll.set_reg_on_off(llh,ll.A,False)
    with d.TaskHandler(['fabry perot control']) as ao:
        d.write_sample(ao,0.0)

if __name__ == '__main__':
    import lockin
    # scan_piezo(0.0,2.50e3,0.125)
    try:
        with wm.WavemeterHandler() as wmh:
            def cb(deltaf,w):
                with lockin.LockinHandler() as lih:
                    x,y = lockin.get_xy(lih)
                r = np.sqrt(x**2 + y**2)
                return False, [
                    'r : {:.3f} mV'.format(1000*r)
                ]
            wo = wm.get_wavenumber(wmh)
            print(wo,'cm-1')
            pre_scan()
            sleep(0.25)
            fp, vth = set_to_fringe_side()
            if fp is None:
                raise Exception('error during setting to fringe side!')
            start_locking(vth)
            # fp, w = relock(wmh,wo,fp)
            # if w is None:
            #     raise Exception('error during relock!')
            # scan_piezo(fp,0.4e3,0.125)
            input('press enter to quit locking')
            # data, success = data_scan(wmh,wo,wo+0.005,fp,2.0,cb)
            # if success is None:
            #     raise Exception('error during scan!')
    finally:
        post_scan()
