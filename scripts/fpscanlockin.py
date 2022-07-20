import daqmx
import numpy as np
import piezo
import laselock as ll
import wavemeter as wm
import lockin

po = 0.5 # volts

v_th_upper = 100.0e-3 # fppd volts / irpd volt
v_th_lower = 0.1e-3

tau_fast = 1.0e-3 # ms
tau_slow = 40.e-3 # ms
n_peak = 15 # points per peak on fast scan
df_peak = 30 # MHz

dfdt_fast = -df_peak / n_peak / tau_fast # MHz / sec
dfdt_slow = -dfdt_fast*tau_fast/tau_slow

peak_fraction = 0.5

sampling_rate = 200e3 # samples per second

df_fast = dfdt_fast / sampling_rate
df_slow = dfdt_slow / sampling_rate

n_fast = tau_fast * sampling_rate
n_slow = tau_slow * sampling_rate

deltat = 0.01 # response time
deltasamples = int(deltat * sampling_rate) # samples per update

fudge = 1.5
buffersamples = int(fudge*deltasamples)

wait = 0.010 # seconds

INPUT, OUTPUT = 0, 1

reg = ll.A

def cfg_timing(ai,ao,buffersamples=buffersamples):
    for mode, task in ((OUTPUT,ao),(INPUT,ai)):
        daqmx.cfg_samp_clk_timing(
            task,sampling_rate,daqmx.CONT_SAMPS,buffersamples,
            {
                OUTPUT:daqmx.ONBOARD_CLK,
                INPUT:daqmx.get_samp_clk_term(ao)
            }[mode]
        )
        daqmx.set_regeneration_mode(ao,False)

def pre_scan():
    with piezo.PiezoDriverHandler() as pdh:
        piezo.set_piezo_voltage(pdh,po)
    with daqmx.TaskHandler(['fabry perot control']) as ao:
        daqmx.write_sample(ao,0.0)
    with ll.LaseLockHandler() as llh:
        ll.set_reg_setpoint(llh,reg,0.0)
        ll.set_reg_on_off(llh,reg,False)

class FastScanGen:
    def __init__(self):
        self.n = 0

    def generate_samples(self,N):
        self.n += N
        return df_fast * (self.n + np.arange(N))

    def get_sample(self,N):
        return df_fast * N

def avg(old,new,window):
    return old * (window-1)/ window + new * 1 / window

def fast_scan():
    with (
            daqmx.TaskHandler(['fabry perot photodiode','ir photodiode']) as ai,
            daqmx.TaskHandler(['fabry perot control']) as ao
    ):
        cfg_timing(ai,ao)
        sg = FastScanGen()
        update_ao(ao,sg,deltasamples)
        for task in (ai,ao):
            daqmx.start_task(task)
        n_chans = 2
        vavg = None
        triggered = None
        n = 0
        navg = n_fast
        nmax = 3.0e3 / abs(df_fast)
        while True:
            fps, irs = daqmx.read_all(ai,int(1e5),n_chans)
            n_read = len(fps)
            if not n_read:
                continue
            update_ao(ao,sg,n_read)
            for fp, ir in zip(fps,irs):
                v = fp / ir
                if vavg is None:
                    vavg = v
                vavg = avg(vavg,v,navg)
                if n > navg:
                    if vavg < v_th_lower:
                        if triggered is True:
                            for task in (ao,ai):
                                daqmx.stop_task(task)
                            samples_generated = daqmx.get_samps_generated(ao) 
                            freq_final = sg.get_sample(samples_generated)
                            print('fast scan done!','fp: {} MHz'.format(str(round(freq_final,1)).rjust(8)))
                            return freq_final
                        if triggered is None:
                            triggered = False
                    if vavg > v_th_upper:
                        if triggered is False:
                            print('triggered!')
                            triggered = True
                if n > nmax:
                    print('fast scan went too far (2.5 GHz). everything ok?')
                    return None
                n += 1

delay = 20000 # samples
scale = 12.5 / 10.0 # MHz piezo dither per volt laselock monitor dither

class SlowScanGen:
    def __init__(self,fo):
        self.fo = fo
        self.n = 0
        self.indither = [0.0] * delay

    def generate_samples(self,N):
        outdither, self.indither = np.array(self.indither[:N]), self.indither[N:]
        samples = self.fo + df_slow * (self.n + np.arange(N)) + outdither
        self.n += N
        return samples

    def import_samples(self,samples):
        self.indither.extend(
            [scale*sample for sample in samples]
        )

    def get_sample(self,N):
        return self.fo + df_slow * N

v_th_slow = 0.100 # volts
POS, NEG = +1, -1
polarity = POS

def slow_scan(fo):
    sg = SlowScanGen(fo)
    class ScanVars:
        def __init__(self):
            self.vavg = None
            self.triggered = False
            self.n = 0
    sv = ScanVars()
    navg = n_slow
    def slow_scan_cb(in_data):
        es, = in_data
        for v in es:
            if sv.vavg is None:
                sv.vavg = v
            sv.vavg = vavg = avg(sv.vavg,v,navg)
            n = sv.n
            triggered = sv.triggered
            if n % navg >= navg - 1:
                print(
                    '{:.1f} MHz'.format(
                        sg.get_sample(n)-sg.get_sample(0)
                    ).rjust(15),
                    '{:.1f} mv'.format(1000*vavg).rjust(10)
                )
            if n > delay:
                if triggered is True:
                    if polarity * vavg < 0:
                        print('slow scan done!')
                        return True, True
                if triggered is False:
                    if {
                            POS:vavg > v_th_slow,
                            NEG:vavg < -v_th_slow
                    }[polarity]:
                        print('triggered!')
                        sv.triggered = True
            sv.n += 1
            if abs(n * df_slow) > 300.0:
                print('past 150.0 MHz. wrong polarity?')
                return True, None
        return False, None
    samples_generated, success = locking_loop(['fabry perot error'],deltasamples,sg,slow_scan_cb)
    fp = sg.get_sample(samples_generated)
    return fp, success

def update_ao(ao,sg,n):
    if n:
        daqmx.write_to_buff(ao,sg.generate_samples(n))

rt = 0.1 # seconds
ramp_samples = int(rt * sampling_rate)
class DataScanGen:
    def __init__(self,fo):
        self.f = fo
        self.n = 0
        self.ramp = np.empty(0)
        self.indither = [0.0] * delay

    def generate_samples(self,N):
        outdither, self.indither = np.array(self.indither[:N]), self.indither[N:]
        ramp, self.ramp = self.ramp[:N], self.ramp[N:]
        if len(ramp) < N:
            ramp = np.hstack((ramp,self.f*np.ones(N-len(ramp))))
        samples = ramp + outdither
        self.n += N
        return samples

    def set_f(self,f):
        self.ramp = np.linspace(self.get_f(),f,ramp_samples)
        self.f = f

    def import_samples(self,samples):
        self.indither.extend(
            [scale*sample for sample in samples]
        )

    def get_n(self):
        return self.n

    def get_f(self):        
        return self.ramp[0] if self.ramp.size else self.f

class Locker:
    def __init__(self,wmh,sg,navg,llh):
        self.navg = navg
        self.wmh = wmh
        self.sg = sg
        self.fp_avg = None
        self.n = 0
        self.new_async()
        self.fps = []
        self.llh = llh
        self.locking = False

    def new_async(self):
        self.async_wm = wm.AsyncWavenumber(self.wmh)

    def check_async(self):
        return self.async_wm.get_wavenumber()

    def check_fps(self,fps):
        navg = self.navg
        fp_avg = self.fp_avg
        for fp in fps:
            self.fps.append(fp)
            if fp_avg is None:
                fp_avg = fp
            fp_avg = avg(fp_avg,fp,navg)
            if self.n > navg and fp_avg < fpmin:
                # plt.plot(fps)
                # plt.show()
                # print(self.n,fp_avg)
                print('lock lost (fabry perot below threshold)!')
                return True
            self.n += 1
            if self.n > delay and not self.locking:
                self.locking = True
                print('starting locking')
                ll.set_reg_on_off(self.llh,reg,True)
        self.fp_avg = fp_avg
        return False

    def cb(self,in_data):
        fps, = in_data
        below_thresh = self.check_fps(fps)
        if below_thresh:
            return True, None
        w_ready, w = self.check_async()        
        if not w_ready:
            return False, None
        self.new_async()
        return self.handle_wnum(w)

    def handle_wnum(self,w):
        return True, None

dfdw = 30e3 # MHz per cm-1
dfmax = 15.0 # MHz

class Hopper(Locker):
    def __init__(self,*args):
        super().__init__(*args)
        self.wprev = None

    def handle_wnum(self,w):
        if self.wprev is not None:
            dw = w - self.wprev
            if abs(dw) > dwmax:
                print('mode hop detected!')
                return True, None
        quitting, result = self.hopper_handoff(w)
        self.wprev = w
        return quitting, result

    def hopper_handoff(self,w):
        return True, None

def data_scan(wmh,fo,wo,df,deltaf,cb):
    sg = DataScanGen(fo)
    navg = n_fast
    with (
            lockin.LockinHandler() as lih,
            ll.LaseLockHandler() as llh
    ):
        scanner = Scanner(wo,df,deltaf,cb,lih,wmh,sg,n_fast,llh)
        samples_generated, result = locking_loop(
            ['fabry perot photodiode'],int(sampling_rate*resp_time),sg,scanner.cb
        )
        ll.set_reg_on_off(llh,reg,False)
        return result
BACKWARDS, FORWARDS = 0, 1
class Scanner(Hopper):
    def __init__(self,wo,df,deltaf,data_cb,lockin_handle,*args):
        super().__init__(*args)
        self.dwmax = 0.002
        self.wo = wo
        self.wp = self.wo + deltaf/dfdw
        self.first = True
        self.df = df
        self.fo = self.sg.get_f()
        self.data_cb = data_cb
        self.lih = lockin_handle
        self.direction = {
            True:FORWARDS,False:BACKWARDS
        }[deltaf > 0]

    def hopper_handoff(self,w):
        if w > self.wp:
            print('scan done!')
            return True, w
        if self.first:
            self.first = False
            dw = w-self.wo
            if abs(dw) > self.dwmax:
                print(
                    '{} exceeds wo ({}) by {}, greater than thresh ({})!'.format(
                        map(
                            '{:.4} cm-1'.format,
                            w,self.wo,dw,self.dwmax
                        )
                    )
                )
                return True, None
        x, y, pd = lockin.get_xya(self.lih)
        f = self.sg.get_f()
        self.sg.set_f(f+{FORWARDS:+1,BACKWARDS:-1}[self.direction]*self.df)
        print(
            'scan:',
            ' | '.join(
                '{}: {}'.format(label,data.rjust(15))
                for label, data in zip(
                    (
                        'deltaf req','deltaf left meas','df meas'
                    ),map(
                        '{:.2f} MHz'.format,
                        (
                            f-self.fo,
                            dfdw*(self.wp-w),
                            (w-self.wprev)*dfdw if self.wprev is not None else 0.0
                        )
                    )
                )
            )
        )
        return self.data_cb(f,x,y,pd,w)

class ReLocker(Hopper):
    def __init__(self,wo,epsilon_f,smoothing,*args):
        super().__init__(*args)
        self.wo = wo
        self.epsilon_f = epsilon_f
        self.smoothing = smoothing

    def hopper_handoff(self,w):        
        df = dfdw*(w-self.wo)        
        print(
            'locking status:',
            ' | '.join(
                '{}: {}'.format(label,data.rjust(15)) for label, data in zip(
                    (
                        'wo','wp','fsg','epf','df'
                    ),
                    [
                        '{:.4f} cm-1'.format(wnum) for wnum in (self.wo,w)
                    ] + [
                        '{:.1f} MHz'.format(freq) for freq in (self.sg.get_f(),self.epsilon_f,df)
                    ]
                )
            )
        )
        if abs(df) < self.epsilon_f:
            print('wnum locked!')
            return True, w
        dfsg = -df/self.smoothing
        if abs(dfsg) > dfmax:
            dfsg = {True:+1,False:-1}[dfsg > 0]*dfmax
        self.sg.set_f(self.sg.get_f()+dfsg)
        return False, None

fpmin = 0.001
resp_time = 0.099
dwmax = 0.050
def relock(wmh,wo,fo,epsilon_f,smoothing):
    with ll.LaseLockHandler() as llh:
        sg = DataScanGen(fo)
        navg = n_fast                    
        locker = ReLocker(wo,epsilon_f,smoothing,wmh,sg,navg,llh)
        samples_generated, w = locking_loop(
            ['fabry perot photodiode'],
            int(sampling_rate*resp_time),sg,locker.cb
        )
        ll.set_reg_on_off(llh,reg,False)
        return sg.get_f(), w

def locking_loop(in_chans,chunk_samples,sg,cb):
    with (
            daqmx.TaskHandler(['fabry perot dither'] + list(in_chans)) as ai,
            daqmx.TaskHandler(['fabry perot control']) as ao
    ):
        cfg_timing(ai,ao,int(fudge*buffersamples))
        update_ao(ao,sg,chunk_samples)
        n_total = 0
        n_chans = daqmx.get_num_chans(ai)
        for task in (ai,ao):
            daqmx.start_task(task)
        while True:
            dithers, *in_data = daqmx.read_all(ai,int(1e5),n_chans)
            sg.import_samples(dithers)
            n_read = len(dithers)
            update_ao(ao,sg,n_read)            
            n_total += n_read
            if n_read:
                quitting, result = cb(in_data)
                if quitting:
                    for task in (ao,ai):
                        daqmx.stop_task(task)
                        samples_generated = daqmx.get_samps_generated(ao) 
                    return samples_generated, result
            
def start_locking():
    with ll.LaseLockHandler() as llh:
        ll.set_reg_on_off(llh,ll.A,True)

def post_scan():
    with ll.LaseLockHandler() as llh:
        ll.set_reg_on_off(llh,ll.A,False)
    with daqmx.TaskHandler(['fabry perot control']) as ao:
        daqmx.write_sample(ao,0.0)

if __name__ == '__main__':
    from matplotlib import pyplot as plt
    
    with wm.WavemeterHandler() as wmh:
        print('setting up scan')
        pre_scan()
        print('starting fast scan')
        fp = fast_scan()
        if fp is None:
            print('fast scan failed')
            raise Exception()
        wo = wm.get_wavenumber(wmh)
        print('starting slow scan')
        fp, success = slow_scan(fp)
        if success is None:
            print('slow scan failed')
            raise Exception()
        # print('starting locking')
        # start_locking()
        print('relocking')
        fp, wp = relock(wmh,wo,fp,5.0,2.5)
        xs = []
        fs = []
        ws = []
        fps = []
        def test_data_cb(f,x,y,fp,w):
            xs.append(x)
            fs.append(f)
            ws.append(w)
            fps.append(fp)
            return False, None
        print('data scanning')
        result = data_scan(wmh,fp,wp,1.0,120.0,test_data_cb)
        print('cleaning up')
        post_scan()
        if result:
            plt.plot(fs,xs,'.')
            plt.show()
            plt.plot(fs,ws,'.')
            plt.show()
        else:
            print('scan failed!')


