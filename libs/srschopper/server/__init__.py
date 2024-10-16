import beckhttpserver as bhs
from srschopper import device as d

class SRSChopperApp(bhs.BeckApp):
    def __init__(self,handle):
        self.s = handle

    @bhs.command('get delay')
    def get_delay(self):
        return d.get_delay(self.s)
    
    @bhs.command('get control')
    def get_control(self):
        return d.get_control(self.s)
    
    @bhs.command('set control')
    def set_control(self,control):        
        return d.set_control(self.s,control)
    
    @bhs.command('get locking')
    def get_locking(self):
        return d.get_locking(self.s)
    
    @bhs.command('set locking')
    def set_locking(self,locking):
        return d.set_locking(self.s,locking)
    
    @bhs.command('get setpoint')
    def get_setpoint(self):
        return d.get_setpoint(self.s)
    
    @bhs.command('set setpoint')
    def set_setpoint(self,setpoint):
        return d.set_setpoint(self.s,setpoint)