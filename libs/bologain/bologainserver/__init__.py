import beckhttpserver as bhs
import daqmx

X10 = 10
X100 = 100
X200 = 200
X1000 = 1000

gain_d = {
    X10:'bolo gain 10',
    X100:'bolo gain 100',
    X200:'bolo gain 200',
    X1000:'bolo gain 1000'
}

class BoloGainApp(bhs.BeckApp):
    def __init__(self,gain=X10):
        self.lines = []        
        self._set_gain(gain)
        for g in gain_d:
            if g != gain:
                self._unset_gain(g)        
    
    def _set_gain(self,gain):
        self._write_line(gain,True)
        self.gain = gain    

    def _unset_gain(self,gain):
        self._write_line(gain,False)

    def _write_line(self,gain,state):
        with daqmx.LineHandler(gain_d[gain]) as line:
            daqmx.write_line(line,state)

    @bhs.command('set-gain')
    def set_gain(self,gain):   
        if gain == self.gain:
            return             
        old_gain = self.gain
        self._set_gain(gain)
        self._unset_gain(old_gain)        

    @bhs.command('get-gain')
    def get_gain(self):
        return self.gain