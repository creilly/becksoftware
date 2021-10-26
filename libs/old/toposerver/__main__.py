import beckhttpserver as bhs
import topo as topomod
import wavemeter as wm
from topo import topotools as tt
from topo import topotoolsplus as ttp
import os
from time import time, sleep

PORT = 8999

wnum_per_degc = -1.0

cmd = bhs.command

epsilon_motor = 0.002 # mm
epsilon_temperature = 0.002 # degC

base_temperature = 25.000 # degC
base_current = 95.000 # milliamps
damping_factor = 5.0

wmin = 2700 # 2933 # 2700
wmax = 3300 # 3111 # 3300

topo = topomod.CommandClient()

class TopoApp(bhs.BeckApp):
    def __init__(self,damping_factor):
        self.wmh = wm.open_wavemeter()
        self.wnum_set = self.wnum_act = wm.get_wavenumber(self.wmh)
        self.locking = False
        self.damping_factor = damping_factor

    def loop(self):
        self.wnum_act = wact = wm.get_wavenumber(self.wmh)
        dw = wact - self.wnum_set
        tset = topo.get_diode_set_temperature()
        tact = topo.get_diode_act_temperature()
        dt = tact-tset
        mset = topo.get_motor_set_pos()
        mact = topo.get_motor_act_pos()
        dm = mact-mset
        # print(
        #     'wact: %f\tdw: %f\ttset: %f\tdt: %f\tmset: %f\tdm: %f' % (
        #         wact, dw, tset, dt, mset, dm
        #     )
        # )
        if wact < wmin or wact > wmax:
            return
        if not self.locking:
            return
        # if (abs(dt) > epsilon_temperature) or (abs(dm) > epsilon_motor):
        # if not topomod.get_diode_temperature_ready():
        #     return
        if abs(dm) > epsilon_motor:
            return
        dtset = - dw / wnum_per_degc / self.damping_factor
        topo.set_diode_temperature(tact+dtset)

    @cmd('get-locking')
    def get_locking(self):
        return self.locking

    @cmd('set-locking')
    def set_locking(self,locking):
        self.locking = locking

    @cmd('get-wavenumber-act')
    def get_wavenumber_act(self):
        return self.wnum_act

    @cmd('get-wavenumber-set')
    def get_wavenumber_set(self):
        return self.wnum_set

    @cmd('set-wavenumber')
    def set_wavenumber(self,wavenumber):
        self.set_locking(False)
        wo = wavenumber
        if wo < wmin or wo > wmax:
            raise bhs.BeckError(
                'requested wnum of {:.5f} outside of bounds {:.5f} < wnum < {:.5f}'.format(
                    wo,wmin,wmax
                )
            )
        self.wnum_set = wo
        topo.set_diode_current(base_current)
        topo.set_diode_temperature(base_temperature)
        while not topomod.get_diode_temperature_ready():
            continue        
        e = int(min(tt.get_etalon(wavenumber),key=lambda x: x[1])[1])
        m = tt.get_motor(wavenumber)
        # e,m,w,dw,p = ttp.lookup_wnum(wo)
        topo.set_motor_pos(m/1000)
        topo.set_etalon_pos(e)

    @cmd('set-line')
    def set_line(self,branch,j,A,dw):
        self.set_locking(False)
        wo, es, ei, ms, mi = ttp.get_line(branch,j,A)
        print(wo,es,ei,ms,mi)
        wo += dw
        print('adjusting wo to:',wo)
        self.wnum_set = wo
        topo.set_diode_current(base_current)
        topo.set_diode_temperature(base_temperature)
        while not topomod.get_diode_temperature_ready():
            continue        
        e = int(es*wo + ei)
        loops = 0
        while True:
            loops += 1
            print('e set',e)
            topo.set_etalon_pos(e)        
            m = ms*wo + mi
            print('mo',m)
            topo.set_motor_pos(m)
            deltawthresh = 0.75
            dwthresh = 0.001
            wthresh = 2800
            wp = 0
            while True:
                wpp = wm.get_wavenumber(self.wmh)
                print('wpp',wpp,wpp-wo)
                if wpp < wthresh:
                    continue
                print('dw',abs(wpp-wp),dwthresh)
                if abs(wpp - wp) < dwthresh:
                    break
                wp = wpp
            deltaw = wpp-wo
            print('wpp',wpp,deltaw)
            mp = ms*wpp + mi
            print('mp',mp)
            topo.set_motor_pos(mp)
            if abs(deltaw) < deltawthresh:
                break
            e = int(e-es*deltaw)
            if loops > 4:
                print('too many trials')
                return self.set_wavenumber(wo)
            print('going for another loop')
        self.wnum_act = wpp

    @cmd('get-damping')
    def get_damping(self):
        return self.damping_factor

    @cmd('set-damping')
    def set_damping(self,damping):
        self.damping_factor = damping

    def shutdown(self):
        wm.close_wavemeter(self.wmh)
        print('shutting down')

if __name__ == '__main__':
    bhs.run_beck_server(PORT,os.path.dirname(__file__),TopoApp,damping_factor,_debug=False)
