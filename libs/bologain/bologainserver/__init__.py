import beckhttpserver as bhs
import daqmx
from bologain import X10, X100, X200, X1000, set_gain

class BoloGainApp(bhs.BeckApp):
    def __init__(self,handle,gain=X10):        
        self.handle = handle
        self._set_gain(gain)        
    
    def _set_gain(self,gain):
        set_gain(self.handle,gain)        
        self.gain = gain        

    @bhs.command('set-gain')
    def set_gain(self,gain):   
        if gain == self.gain:
            return             
        self._set_gain(gain)

    @bhs.command('get-gain')
    def get_gain(self):
        return self.gain