import topo, wavemeter as wm, interrupthandler, oscilloscope as scope, \
    numpy as np, hitran, argparse, beckasync, interrupthandler, opo as opomod
from topo import topotoolsplus as ttp
from time import sleep

np.random.seed()

To = 25.0
Io = 95.0
Vo = 20.0

tau = 1.00 # seconds
tau_rest = 3 * tau
dm = 0.005 # mm
deltam = 0.18 # mm
backlash = 0.050 # mm
signal_power_offset = 51 # mw
def optimize_motor(mo,ih):    
    motor_positions = ms = mo + np.arange(0,deltam,dm) - deltam / 2
    signal_powers = []
    measured_positions = []
    topo.set_motor_pos(motor_positions[0]-backlash)
    sleep(tau_rest)
    ic = topo.InstructionClient()
    for motor_position in motor_positions:
        if ih.interrupt_received():                
                ih.raise_interrupt()
        ic.set_motor_pos(motor_position)
        sleep(tau)
        measured_positions.append(ic.get_motor_act_pos())
        signal_power = ic.get_signal_power()
        signal_powers.append(signal_power - signal_power_offset)
        print(
            ' : '.join(
                '{:.3f}'.format(f,3) for f in (motor_positions[0],motor_position,motor_positions[-1])
            ), '|', '{:d} mw'.format(int(round(signal_power))).rjust(12)
        )
    mum = sum(
        motor_position * signal_power 
        for motor_position, signal_power in 
        zip(motor_positions,signal_powers)
    ) / sum( signal_powers )
    print('mu m: {:.3f} mm'.format(mum))
    assert mum < 10 and mum > 2
    topo.set_motor_pos(motor_positions[0] - backlash)
    topo.set_motor_pos(mum)    
    pmax = ic.get_input(topo.FAST4)
    return pmax, mum

def get_stable_wavenumber_with_dither_async(wmh,ic):
    while True:
        w = yield from get_stable_wavenumber_async(wmh)
        if w is W_UNSTABLE:
            print('wavemeter reading unstable. dithering piezo.')
            dither_piezo(ic)
            continue
        if w is W_NOSIGNAL:
            return W_NOSIGNAL
        return w    

def get_stable_wavenumber_with_dither(wmh,ic,ih):
    return handle_interrupt(get_stable_wavenumber_with_dither_async(wmh,ic),ih)

def dither_piezo(ic : topo.InstructionClient):
    pv = get_random_piezo()
    ic.set_piezo(pv)
    return pv

def get_random_piezo():
    pzo, dpz = 5.0, 20.0
    return pzo + dpz*np.random.random()

class LineSetError(Exception): pass    
def set_etalon_motor(ic : topo.InstructionClient,wtarget,eo,mo,es,ms,pv,wmh,ih,opo):    
    print('setting initial e + m pair:',eo,round(mo,3))        
    ic.set_etalon_pos(eo)
    ic.set_piezo(pv)
    e = eo
    m = mo        
    while True:
        print('optimizing motor:')           
        if opo:
            opo = False
            topo.set_motor_pos(m-backlash)
            topo.set_motor_pos(m)
            pmax = ic.get_input(topo.FAST4)
        else:
            pmax, m = optimize_motor(m,ih)        
        print('waiting for diode temp to stabilize...')        
        while not ic.get_diode_temperature_ready():
            continue
        print('done.')              
        w = get_stable_wavenumber_with_dither(wmh,ic,ih)
        if w is W_NOSIGNAL:
            def walk_opo():
                deltae = es * deltaw
                deltam = ms * deltaw
                print('delta w',deltaw,'deltae',deltae,'deltam',deltam)
                topo.set_motor_pos(mo + deltam)
                ic.set_etalon_pos(int(round(eo + deltae)))
            print('no wavemeter signal, dithering etalon')
            dw = +0.25 # cm-1
            deltaw = dw
            while True:     
                walk_opo()
                w = get_stable_wavenumber_with_dither(wmh,ic,ih)
                if w is W_NOSIGNAL:
                    print('no wavemeter signal still...')
                    deltaw += dw
                    continue                
                success = True
                while deltaw > 0:
                    deltaw -= dw / 2
                    walk_opo()                    
                    w = get_stable_wavenumber_with_dither(wmh,ic,ih)
                    if w is W_NOSIGNAL:
                        print('lost signal, starting again...')
                        success = False
                        break
                if success:
                    break
                else:
                    deltaw += dw
            continue
        dw = w - wtarget
        dwthresh = 1.00
        print('post motor opt dw:',round(dw,3),'dw thresh:',dwthresh)
        if abs(dw) < dwthresh:
            print('e + m tuning below thresh. continuing...')
            return w, pmax, e, m
        else:
            de = -int(round(es * dw))
            e += de
            pv = dither_piezo(ic)
            print('dithering piezo to {:.2f} volts'.format(pv))
            topo.set_piezo(pv)
            print('adding',de,'to etalon. now etalon is',e)
            topo.set_etalon_pos(e)

W_UNSTABLE = None
W_NOSIGNAL = -1
def get_stable_wavenumber_async(wmh : wm.WavemeterHandler):    
    print('starting stable wavemeter acquisition')
    wo = None
    dwthresh = 0.0015
    wthresh = 2800
    trial = 0
    trials = 5
    unstable_trial = 0
    unstable_trials = 5
    nosignal_trial = 0
    nosignal_trials = 5
    while True:        
        w = yield from wm.get_wavenumber_async(wmh)
        print('{:.4f} cm-1'.format(w).rjust(15), 't', trial, 'ut', unstable_trial, 'nst', nosignal_trial)
        if w < wthresh:
            trial = 0
            nosignal_trial += 1
            if nosignal_trial == nosignal_trials:
                return W_NOSIGNAL
            continue        
        if wo is None:
            wo = w
        else:
            dw = w - wo
            if abs(dw) < dwthresh:
                trial += 1
                if trial == trials:
                    return w
            else:
                trial = 0
                unstable_trial += 1
                if unstable_trial == unstable_trials:
                    return W_UNSTABLE  
        wo = w

def handle_interrupt(gen,ih : interrupthandler.InterruptHandler):
    try:
        while True:
            next(gen)
            if ih.interrupt_received():
                ih.raise_interrupt()
    except StopIteration as si:
        return si.value
    
def get_stable_wavenumber(wmh : wm.WavemeterHandler, ih : interrupthandler.InterruptHandler):    
    return handle_interrupt(get_stable_wavenumber_async(wmh),ih)

def tune_diode_temperature_async(
    ic : topo.InstructionClient,
    wmh : wm.WavemeterHandler, 
    wtarget : float, w : float
):
    epsilonT = 0.005
    epsilont = 0.010 # seconds
    dwthresh = 0.00075 # cm-1, desired accuracy    
    dTmax = 0.30 # cm-1
    damping = 2.5
    ditherthresh = 2.0
    dithercutoff = 0.005
    dwdt = -1.0 # cm-1 per deg C (fix this!)
    wo = w    
    trial = 0
    trials = 4
    trial_threshold = 0.002
    ic = topo.InstructionClient()
    while True:        
        werr = wo - wtarget
        dT = -werr/dwdt/damping
        if abs(dT) > dTmax:
            dT = {True:+1,False:-1}[dT > 0] * dTmax
        To = ic.get_diode_set_temperature()
        Tp = To + dT
        Ts = np.linspace(To,Tp,max(int(abs(dT/epsilonT)),5))        
        for T in Ts:
            ic.set_diode_temperature(T)
            yield from beckasync.sleep(epsilont)
        ic.set_diode_temperature(Tp)        
        w = yield from wm.get_wavenumber_async(wmh)
        dwo = wo - wtarget
        dw = w - wtarget
        print('dw','{:+.4f} cm-1'.format(dw),'Tp','{:.5f} deg C'.format(Tp))              
        if max(map(abs,(dwo,dw))) > dithercutoff and abs((dwo-dw) / dwo) > ditherthresh:
            print('small mode hop detected. dithering piezo.')                        
            while True:
                dither_piezo(ic)
                w = yield from get_stable_wavenumber_with_dither_async(wmh,ic)                
                if w is W_NOSIGNAL:
                    raise Exception('no wavemeter signal')
                break
        if not trial:
            if ic.get_diode_temperature_ready() and abs(dw) < dwthresh:                
                trial += 1
        else:
            if abs(dw) < trial_threshold:
                if ic.get_diode_temperature_ready():
                    trial += 1                    
                    if trial == trials:                    
                        print('tuning successful')
                        return w
            else:                
                trial = 0
        wo = w

def tune_diode_temperature(
    ic : topo.InstructionClient,
    wmh : wm.WavemeterHandler, 
    wtarget : float, w : float,
    ih : interrupthandler.InterruptHandler
):
    return handle_interrupt(
        tune_diode_temperature_async(ic,wmh,wtarget,w),
        ih
    )

OPO_LATEST = -1
def set_line(htline,dw,wmh=None,opo=False,opo_entry=OPO_LATEST,ih=None):    
    if opo:
        if opo_entry == OPO_LATEST:
            opod = opomod.open_latest(htline)               
        else:
            if opo_entry in opomod.get_entries(htline):
                opod = opomod.open_entry(htline,opo_entry)
            else:
                opod = None
    else:
        opod = None
    if opod is None:
        em = pv = dt = None
        opo = False
    else:
        em = (opod[opomod.ETALON], opod[opomod.MOTOR])        
        pv = opod[opomod.PIEZO]
        dt = opod[opomod.TEMPERATURE]
    wo = hitran.lookup_line(htline)[hitran.WNUMBECK]    
    return set_omega(wo,dw,wmh,opo=opo,em=em,pv=pv,dt=dt,ih=ih)

def set_omega(wo,dw,wmh=None,opo=False,em=None,pv=None,dt=None,ih=None):
    ic = topo.InstructionClient()   
    if opo:
        assert None not in (em,pv,dt)
    if pv is None:
        pv = Vo
    if dt is None:
        dt = To
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
            if em is not None:
                eo, mo = em
                eo = int(round(eo))
            else:
                eo = e
                mo = m
            with scope.ScopeHandler() as sh:
                ws_enabled = scope.get_wavesource_enabled(sh)
                scope.set_wavesource_enabled(sh,False)
            try:
                ic.set_diode_temperature(dt)
                ic.set_diode_current(Io)                
                while True:                    
                    wp, pmax, e, m = set_etalon_motor(ic,w,eo,mo,es,ms,pv,wmh,ih,opo)
                    wp = tune_diode_temperature(ic,wmh,w,wp,ih)                                    
                    return wp, pmax, e, m                    
            finally:
                with scope.ScopeHandler() as sh:
                    scope.set_wavesource_enabled(sh,ws_enabled)
        finally:
            if close_on_exit:
                wm.close_wavemeter(wmh)

PARA, ORTHO, META = 0, 1, 2
ALLJ = -1
ALLNU = -1
ALLBRANCH = -1
ALLSPIN = -1
def line_wizard(spin,nuo,nup,j,jmax,branch):    
    filt = lambda foo, l: [*filter(foo,l)]
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
        if stage in (GLQ,GUQ):            
            def gq_filter(level):
                def _gq_filter(rawgq):
                    nus, sym, level = hitran.parse_gq(rawgq)                    
                    _nus = {
                        GLQ:nuo,GUQ:nup
                    }[stage]
                    return nus == tuple(_nus) if _nus != ALLNU else True                        
                return _gq_filter
            entries = filt(
                gq_filter(stage),
                entries
            )                      
        if stage == LLQ:  
            def llq_filter(rawllq):
                jp, symp, lp = hitran.parse_lq(rawllq)
                return (
                    jp == j
                    if j != ALLJ else 
                    jp <= jmax
                ) and (
                    symp[0] == {
                        0:'E',1:'F',2:'A'
                    }[spin] if spin != ALLSPIN else True
                )                                         
            entries = filt(llq_filter,entries)
        if stage == LUQ:            
            jo, symo, lo = hitran.parse_lq(htline[-1])
            def glq_filter(rawglq):                
                jp, symp, lp = hitran.parse_lq(rawglq)                
                return (
                    jp - jo == branch
                ) if branch != ALLBRANCH else True     
            entries = filt(glq_filter,entries)
        if len(entries) == 1:
            htline.append(entries[0])            
            stage += 1
            continue
        if len(entries) == 0:
            print('no entries matching criteria!')
            return None
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
    return htline

if __name__ == '__main__':
    import opo
    import tclock
    ap = argparse.ArgumentParser()
    YES, NO = 'y', 'n'    
    boold = {
        YES:True,NO:False
    }
    options = (YES,NO)
    ap.add_argument(
        '--opo','-o',choices=(YES,NO),default=YES,help='look up values in opo db? ([y] or [n])',
    )
    ap.add_argument(
        '--code','-c',type=int,default=OPO_LATEST,help='entry code to look up in opo dp (latest = {:d})'.format(OPO_LATEST)
    )
    ap.add_argument(
        '--update','-u',choices=(),default=YES,help='update opo db after set? ([y] or [n])'
    )
    ap.add_argument(
        '--tc','-t',default=NO,choices=(YES,NO),help='lock to transfer cavity? ([y] or [n])'
    )
    ap.add_argument(
        '--wavenum','-w',default=-1,type=float,help='set topo to specified wavenumber (skips line selection)'
    )
    ap.add_argument(
        '--spin','-s',default=ALLSPIN,type=int,choices=(META,ORTHO,PARA),help='nuclear spin isomer (para=0, ortho=1, meta=2)'
    )   
    ap.add_argument(
        '--jmax','-x',default=10,type=int,help='max initial j to display'
    )
    ap.add_argument(
        '--j','-j',default=ALLJ,type=int,help='lower j level'
    )
    ap.add_argument(
        '--nuo','-v',default=ALLNU,type=int,nargs=4,help='lower nu quanta (e.g. 0 1 0 1 for v2v4 comb band)'
    )
    ap.add_argument(
        '--nup','-p',default=ALLNU,type=int,nargs=4,help='upper nu quanta (e.g. 0 1 0 1 for v2v4 comb band)'
    )
    ap.add_argument(
        '--dw','-d',default=0.0,type=float,help='wavemeter offset (cm-1)'
    )
    ap.add_argument(
        '--branch','-b',type=int,default=ALLBRANCH,help='branch (p = -1, q = 0, r = +1)'
    )
    args = ap.parse_args()
    w = args.wavenum    
    opob = boold[args.opo]
    code = args.code
    update = boold[args.update]
    tc = boold[args.tc]    
    dw = args.dw
    htline = line_wizard(args.spin,args.nuo,args.nup,args.j,args.jmax,args.branch)
    if htline is None:
        print('no line found!')
        exit(1)
    print('selected line: {}'.format(hitran.fmt_line(htline)))    
    print('setting line...')   
    if tc:
        while True:
            success, (e, m, f, w) = tclock.locktc(htline,dw,opo=opob,opo_entry=code)
            if not success:
                print('tc lock failed. retrying...')
            break
    else:
        w, _, e, m = set_line(htline,dw,opo = opob,opo_entry=code)
    print('line set.')
    if update:
        ic = topo.InstructionClient()                
        pv = ic.get_piezo()
        opo.add_entry(htline,e,m,pv,topo.get_diode_set_temperature(),w)