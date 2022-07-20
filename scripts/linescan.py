import topo
import wavemeter as wm
import interrupthandler
import oscilloscope as scope
import daqmx
from topo import topotoolsplus as ttp
import numpy as np
import hitran
from time import sleep
import argparse

To = 25.0
Io = 95.0
Vo = 20.0

def start_acq(ai):
    daqmx.start_task(ai)

def read_acq(ai):
    daqmx.task_wait(ai)
    data = daqmx.read_buff(ai,daqmx.get_samps_acquired(ai))[0]
    daqmx.stop_task(ai)
    return sum(data)/len(data)

DELTAM = 0.005
def optimize_motor(mo,ih):
    dm = 0.002
    sign = +1.0
    N = 3
    n = 0
    poo = None
    po = None
    pp = None
    increasing = None
    ps = []
    ms = []
    pos = []
    m = mo-sign*DELTAM
    trial = 0
    with daqmx.TaskHandler(['ir photodiode']) as ai:
        samprate = 10e3 # samps per sec
        samptime = 0.075 # seconds
        daqmx.cfg_samp_clk_timing(
            ai,
            samprate,
            daqmx.FINITE_SAMPS,
            int(samptime*samprate)
        )
        while True:
            if ih.interrupt_received():                
                ih.raise_interrupt()                
            topo.set_motor_pos(m)
            n += 1
            start_acq(ai)
            p = read_acq(ai)
            ps.append(p)
            ms.append(m)
            if po is None:
                po = p
                poo = p
            pos.append(po)
            pp = (N-1)/N*po + 1/N*p
            print('po:','{:.1f} mv'.format(1000*po),'n:','{:02d}'.format(n),'sign:',int(sign),'inc?:',increasing)
            if len(ps) > N:
                if pp > po:
                    increasing = True
                if pp < poo:
                    ps,ms,pos = map(np.array,(ps,ms,pos))
                    if increasing:
                        mmax = ms[ps.argmax()]
                        pmax = ps.max()
                        print('pmax',int(1000*pmax),'mv')
                        topo.set_motor_pos(mmax)
                        break
                    else:
                        print('changing direction...')
                        trial += 1
                        if trial > 4:
                            print('number of trials > 4. jostling TOPO cavity piezo...')
                            topo.set_piezo(20.0+5.0*np.random.random())
                        ps = []
                        ms = []
                        pos = []
                        sign *= -1
                        increasing = None
            po = pp
            m += sign * dm
    return pmax, mmax

def get_stable_w(wmh,ih):
    wo = None
    dwthresh = 0.001
    wthresh = 2800
    while True:
        if ih.interrupt_received():            
            ih.raise_interrupt()            
        w = wm.get_wavenumber(wmh)
        if w < wthresh:
            print(
                'wavemeter reading of {:.4f} cm-1 below threshold. rereading...'.format(w)
            )
            continue
        if wo is None:
            wo = w
        else:
            dw = w - wo
            if abs(dw) < dwthresh:
                return w
            else:
                print('wavemeter reading unstable (dw {:.4f} cm-1). rereading...'.format(dw))
                wo = w

def set_etalon_motor(wtarget,eo,mo,es,ms,wmh,ih):
    print('setting initial e + m pair:',eo,round(mo,3))
    topo.set_etalon_pos(eo)
    e = eo
    m = mo
    while True:
        print('optimizing motor:')
        pmax, m = optimize_motor(m,ih)
        w = get_stable_w(wmh,ih)
        dw = w - wtarget
        dwthresh = 0.55
        print('post motor opt dw:',round(dw,3),'dw thresh:',dwthresh)
        if abs(dw) < dwthresh:
            print('e + m tuning below thresh. continuing...')
            return w, pmax, e, m
        else:
            de = -int(round(es * dw))
            e += de
            pv = 20.0+5.0*np.random.random()
            print('dithering piezo to {:.2f} volts'.format(pv))
            topo.set_piezo(pv)
            print('adding',de,'to etalon. now etalon is',e)
            topo.set_etalon_pos(e)
            
def tune_diode_temperature(wtarget,winit,wmh,ih):
    deltawthresh = 0.2 # cm-1, detect mode hops
    dwthresh = 0.0005 # cm-1, desired accuracy    
    damping = 5.0
    dwdt = -1.0 # cm-1 per deg C (fix this!)
    wo = winit
    while True:
        if ih.interrupt_received():
            ih.raise_interrupt()
        werr = wo - wtarget
        dT = -werr/dwdt/damping
        Tp = topo.get_diode_act_temperature()+dT
        print('werr','{:.4f} cm-1'.format(werr),'Tp','{:.5f} deg C'.format(Tp))
        topo.set_diode_temperature(Tp)
        w = wm.get_wavenumber(wmh)
        deltaw = w - wo
        if abs(deltaw) > deltawthresh:
            print('mode hop detected')
            return (False,None)
        dw = w-wtarget
        if abs(dw) < dwthresh and topo.get_diode_temperature_ready():
            print('tuning successful')
            return (True,w)
        wo = w

def set_line(htline,dw,wmh=None,em=None,ih=None):
    class DummyIH:
        def __init__(self,ih):
            self.ih = ih

        def __enter__(self):
            return self.ih

        def __exit__(self,*args):
            pass
    with (
        DummyIH(ih) if ih is not None else
        interrupthandler.InterruptHandler()
    ) as ih:
        if wmh is None:
            wmh = wm.open_wavemeter()
            close_on_exit = True
        else:
            close_on_exit = False
        try:
            wo = hitran.lookup_line(htline)[hitran.WNUMBECK]
            w = wo + dw
            e, es = ttp.get_etalon(w)
            e = int(e)
            m, ms = ttp.get_motor(w)
            print('lut:')
            print(
                '\t' + ', '.join(
                    '{}: {} {}'.format(
                        label, fstr.format(num).rjust(12), unit
                    ) for label, num, fstr, unit in zip(
                        (
                            'w', 'e', 'm', 'dedw', 'dmdw'
                        ),(
                            w, e, m, es, ms
                        ),(
                            '{:.4f}', '{:d}', '{:.3f}', '{:.1e}', '{:.1e}'
                        ),(
                            'cm-1', 'steps', 'mm', 'steps per cm-1', 'mm per cm-1'
                        )
                    )
                )
            )
            dfdw = 30e3 # MHz per cm-1
            if em is not None:
                eo, mo = em
                eo = int(eo)
            else:
                eo = e
                mo = m
            with scope.ScopeHandler() as sh:
                ws_enabled = scope.get_wavesource_enabled(sh)
                scope.set_wavesource_enabled(sh,False)
            try:
                while True:
                    topo.set_diode_temperature(To)
                    topo.set_diode_current(Io)
                    wp, pmax, e, m = set_etalon_motor(w,eo,mo,es,ms,wmh,ih)
                    result, wp = tune_diode_temperature(w,wp,wmh,ih)                
                    if result:
                        return wp, pmax, e, m
            finally:
                with scope.ScopeHandler() as sh:
                    scope.set_wavesource_enabled(sh,ws_enabled)
        finally:
            if close_on_exit:
                wm.close_wavemeter(wmh)

def line_wizard():
    CH4 = 6
    MOL, ISO, GLQ, GUQ, LLQ, LUQ = 0, 1, 2, 3, 4, 5
    def header(index):
        return {
            MOL:'molecule',
            ISO:'isotopologue',
            GLQ:'global lower quanta',
            GUQ:'global upper quanta',
            LLQ:'local lower quanta',
            LUQ:'local upper quanta'
        }[index]
    def formatter(index,entry):
        if index == MOL:
            return {
                CH4:'CH4'
            }[int(entry)]
        if index == ISO:
            return entry
        if index in (GLQ,GUQ):
            return entry
        if index in (LLQ,LUQ):
            j, sym, level = hitran.parse_lq(entry)
            return ', '.join(['j = {: 3d}'.format(j),'level = {: 3d}'.format(level),'sym = {}'.format(sym)])
    def key(index):
        if index not in (LLQ,LUQ):
            return lambda x: x
        def lqkey(entry):
            return hitran.parse_lq(entry)
        return lqkey
    htline = []
    stage = 0
    while True:
        print('')
        print('currently -> [ {} ]'.format(hitran.fmt_line(htline)))
        print('')
        if len(htline) == 6:
            break
        entries = hitran.ls(htline)
        if len(entries) == 1:
            htline.append(entries[0])            
            stage += 1
            continue
        entries = sorted(entries,key=key(stage))
        print(
            '\n'.join(
                '\t{: 3d} : {}'.format(index+1,formatter(stage,entry))
                for index, entry in enumerate(entries)
            )
        )
        index = int(input('select {} : '.format(header(stage)))) - 1
        htline.append(entries[index])        
        stage += 1
    dw = float(input('enter wavemeter offset (cm-1) : '))
    return htline, dw
if __name__ == '__main__':
    import pprint
    htline, dw = line_wizard()
    print('selected line: {}'.format(hitran.fmt_line(htline)))
    print('setting line...')
    set_line(htline,dw)
    print('line set.')