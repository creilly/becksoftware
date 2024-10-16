import topo, time

TOPO, ARGOS = 0, 1

# MHz / Volt
dfdvsd = {
    TOPO:+0.64e3,
    ARGOS:-2.56e3
}

dampingd = {
    TOPO:10,ARGOS:20
}

outputchanneld = {
    TOPO:topo.A,ARGOS:topo.B
}

deltafmax = 2 # MHz
class Locker:
    def __init__(self,control,coefficient,damping):        
        self.f_offset = 0.0
        self.f_setpoint = 0.0
        self.control = control
        self.coeff = coefficient # delta f for unit change in control
        self.damping = damping
    def update(self,f):        
        fp = f - self.f_offset        
        deltaf = (fp - self.f_setpoint)/self.damping
        if abs(deltaf) > deltafmax:
            deltaf = deltafmax * (+1 if deltaf > 0 else -1)
        deltav = -deltaf/self.coeff
        self.control.update(deltav)        
    def set_offset(self,f_offset):
        self.f_offset = f_offset
    def get_offset(self):
        return self.f_offset
    def set_setpoint(self,f_setpoint):
        self.f_setpoint = f_setpoint    
    def get_setpoint(self):
        return self.f_setpoint
    def reset(self):
        self.f_offset = 0.0
    def get_control(self):
        return self.control.get_output()    

class PiezoControl:
    vmin = 0.5 # volts
    vmax = 3.5 # volts
    def __init__(self,laser,ic : topo.AsyncInstructionClient):
        self.outputchannel = outputchanneld[laser]
        self.ic = ic        
        self.mc = topo.MonitoringClient(
            'io:out-{}:voltage-set'.format(
                {topo.A:'a',topo.B:'b'}[self.outputchannel]
            ),topo.FLOAT
        )
        self.v = self.mc.poll()    

    def update(self,deltav):
        self.set_output(self.get_output()+deltav)

    def set_output(self,v):
        v = min(
            PiezoControl.vmax,max(
                PiezoControl.vmin,v
            )
        )        
        self.ic.read_async()
        if not self.ic.queue:
            self.ic.set_output(self.outputchannel,v)        
        self.v = v

    def check_mc(self):
        while True:
            response = self.mc.poll(0)
            if response is None:
                break
            self.v = response        

    def get_output(self):        
        return self.v    