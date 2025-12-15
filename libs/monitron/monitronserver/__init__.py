import beckhttpserver as bhs, lockin, time
from tc import tcclient as tcc, scanner

dt = 1.0
df = 10 # MHz
scan_dir = scanner.Scanner.UP

ON, OFF = 1, 0
class MonitronApp(bhs.BeckApp):    
    def __init__(self,lih):
        self.lih = lih
        self.vs = {
            state:0 for state in (ON,OFF)
        }
        self.to = 0
        self.state = ON
        self.fo = tcc.get_setpoint(scan_dir)        

    def loop(self):
        t = time.time()
        if t > self.to + dt:
            self.vs[self.state] = lockin.get_rt(self.lih)[0]
            self.state = {ON:OFF,OFF:ON}[self.state]
            tcc.set_setpoint(
                scan_dir,
                self.fo + {ON:0,OFF:df}[self.state],
                wait=False
            )
            self.to = t
            
    @bhs.command('get-input')
    def get_input(self):   
        return self.vs[ON] - self.vs[OFF]