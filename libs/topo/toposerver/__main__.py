import beckhttpserver as bhs
import topo as topomod
import wavemeter as wm
from topo import topotools as tt
import os
from time import time

PORT = 8999

wnum_per_degc = -1.0

cmd = bhs.command

epsilon_motor = 0.002 # mm
epsilon_temperature = 0.002 # degC

base_temperature = 25.000 # degC

damping_factor = 10

wnummin = 2700
wnummax = 3300

topo = topomod.CommandClient()

class TopoApp(bhs.BeckApp):
    def __init__(self,damping_factor):        
        self.wnum_set = self.wnum_act = wm.get_wavenumber()
        self.locking = False
        self.damping_factor = damping_factor

    def loop(self):
        self.wnum_act = wact = wm.get_wavenumber()
        dw = wact - self.wnum_set
        tset = topo.get_diode_set_temperature()
        tact = topo.get_diode_act_temperature()
        dt = tact-tset
        mset = topo.get_motor_set_pos()
        mact = topo.get_motor_act_pos()
        dm = mact-mset
        print(
            'wact: %f\tdw: %f\ttset: %f\tdt: %f\tmset: %f\tdm: %f' % (
                wact, dw, tset, dt, mset, dm
            )
        )
        if wact < wnummin or wact > wnummax:
            return
        if not self.locking:
            return
        # if (abs(dt) > epsilon_temperature) or (abs(dm) > epsilon_motor):
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
        self.wnum_set = wavenumber
        topo.set_diode_temperature(base_temperature)
        topo.set_motor_pos(tt.get_motor(wavenumber)/1000)
        topo.set_etalon_pos(tt.get_etalon(wavenumber)[0][1])

    @cmd('get-damping')
    def get_damping(self):
        return self.damping_factor

    @cmd('set-damping')
    def set_damping(self,damping):
        self.damping_factor = damping

    def shutdown(self):
        print('shutting down')

if __name__ == '__main__':
    bhs.run_beck_server(PORT,os.path.dirname(__file__),TopoApp,damping_factor)
