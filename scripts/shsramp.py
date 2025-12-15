from shs import shsclient as shsc
import msvcrt, time, numpy as np, math, sampleheater

COLD, HOT = 0, 1
setpointd = {
    sampleheater.RES:{HOT:350,COLD:300},
    sampleheater.EB:{HOT:800,COLD:300}
} # deg K
res_setpoint = 300 # deg K
slope_setpoint_d = {
    sampleheater.EB:2.0,sampleheater.RES:0.5
} # deg K per second
bufferd = {sampleheater.EB:50,sampleheater.RES:5} # deg K
deltav = 2 # volts
bufferv = 10 # volts
deltat = 0.4 # seconds
dt = 0.04 # seconds
evmax = 1000 # volts
ccmax = 4.7 # amps
deltac = 0.01 # amps
bufferc = 0.1 # amps

class QuitProgram(Exception):
    pass

setpointkey = HOT
locking = False

def heat3_command(foo,*args):
    while True:
        try:
            return foo(*args)
        except ConnectionRefusedError:
            print('connection refused')
            continue
try:    
    while True:
        if msvcrt.kbhit():
            c = msvcrt.getch().decode('utf-8')
            if c == 'q':
                raise QuitProgram()
            if c == 'l':
                locking = True
                print('locking engaged')
            if c == 'u':                
                locking = False
                print('locking disengaged')
            if c == 'h':
                setpointkey = HOT
            if c == 'c':
                setpointkey = COLD
        to = time.time()
        temps = []
        times = []
        while True:            
            t = time.time()
            times.append(t)
            temps.append(heat3_command(shsc.get_temperature))            
            if len(temps) > 1 and t - to > deltat:
                break
            time.sleep(dt)
        temp = np.average(temps)
        slope, _ = np.polyfit(times,temps,1)
        ev = heat3_command(shsc.get_ev)
        ec = heat3_command(shsc.get_ec)
        hm = heat3_command(shsc.get_heating_mode)
        cc = heat3_command(shsc.get_cc)
        cv = heat3_command(shsc.get_cv)
        om = heat3_command(shsc.get_operation_mode)
        evsp = heat3_command(shsc.get_ev_sp)
        ccsp = heat3_command(shsc.get_cc_sp)
        if ec is None:
            ec = math.nan
        temp_sp = setpointd.get(hm,{HOT:300,COLD:300})[setpointkey]
        delta_temp = temp_sp - temp
        buffer = bufferd.get(hm,1)
        slope_setpoint_p = min(abs(delta_temp),buffer) / buffer * (
            +1 if delta_temp > 0 else -1
        ) * slope_setpoint_d.get(hm,0.0)
        print(
            'lk: {},'.format({True:'y',False:'n'}[locking]),
            'om: {},'.format(
                {sampleheater.STANDBY:'sb',sampleheater.OPERATE:'op'}.get(om,'?')
            ).rjust(2),
            'hm: {},'.format(
                {sampleheater.RES:'res',sampleheater.EB:'eb'}.get(hm,'?')
            ).rjust(3),
            ', '.join(
                '{}: {} {}'.format(
                    label, val, units
                ) for label, val, units in zip(
                    ('T','T sp','dTdt','dTdt sp','cc','ccsp','cv','ec','ev','evsp'),
                    [
                        '{{:+.{:d}f}}'.format(n).format(v).rjust(d) 
                        for v, n, d in 
                        (
                            (temp,2,8),(temp_sp,1,7),(slope,2,7),
                            (slope_setpoint_p,2,6),(cc,3,6),(ccsp,3,6),
                            (cv,2,6),(ec*10**3,2,7),(ev,0,6),(evsp,0,6)
                        )
                    ],
                    ('K','K','K/s','K/s','a','a','v','ma','v','v')
                )
            ), '|', 'n: {:d}'.format(len(temps))
        )   
        if locking and om == sampleheater.OPERATE:
            try:
                spo, spact, dsp, spmax, spfunc, spbuffer = {
                    sampleheater.EB:(evsp, ev, deltav, evmax, shsc.set_ev_sp, bufferv),
                    sampleheater.RES:(ccsp, cc, deltac, ccmax, shsc.set_cc_sp, bufferc)
                }.get(hm,[None]*6)
                if spo is None:
                    print('hm not recognized:',hm)
                    continue
                if abs(spact-spo) > spbuffer:
                    print('setpoint too different from actual.')
                    continue
                sp = spo + (+1 if slope < slope_setpoint_p else -1) * dsp
                if sp > spmax:
                    sp = spmax
                if sp < 0:
                    sp = 0
                heat3_command(spfunc,sp)
            except KeyError:                            
                print('unrecognized heating mode:',hm)                
except QuitProgram:
    print('quitting.')