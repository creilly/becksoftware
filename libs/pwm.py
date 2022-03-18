import daqmx as d

buffsize = 100
minticks = 2

def write_voltage(handle,v):
    d.write_ticks(handle,*voltage_to_ticks(v))

class PWM:
    def __init__(self,channel,resolution,vmax,vo,vsafety):
        self.resolution = resolution
        self.vmax = vmax
        self.vsafety = vsafety
        self.co = co = d.create_task()
        self.running = False
        d.create_co_ticks_channel(co,channel,*self._voltage_to_ticks(vo))
        self.set_voltage(vo)
        d.cfg_implicit_timing(co,d.CONT_SAMPS,buffsize)

    def __enter__(self):
        return self

    def __exit__(self,*args):
        self.stop()
        self.clear()

    def _voltage_to_ticks(self,v):
        if v > self.vsafety:
            raise Exception('requested pwm voltage exceeds safety voltage!')        
        highticks = int(round(self.resolution*v/self.vmax))
        lowticks = self.resolution - highticks
        return highticks+minticks,lowticks+minticks        

    def start(self):
        if not self.running:
            d.start_task(self.co)
            self.running = True

    def stop(self):
        if self.running:
            d.stop_task(self.co)
            self.running = False

    def set_voltage(self,v):
        high_ticks, low_ticks = self._voltage_to_ticks(v)
        # print('high ticks',high_ticks,'low ticks',low_ticks)
        {
            True:d.write_ticks,
            False:d.set_ticks
        }[self.running](self.co,high_ticks,low_ticks)
        self.v = v

    def get_voltage(self):
        return self.v

    def get_running(self):
        return self.running

    def set_running(self,running):
        if running:
            self.start()
        else:
            self.stop()

    def clear(self):
        d.clear_task(self.co)
            
if __name__ == '__main__':
    resolution = 5000
    vmax = 12.0    
    vo = 1.5
    vsafety = 2.5
    with PWM(
        'transfer cavity heater',
        resolution,
        vmax,
        vo,
        vsafety
    ) as pwm:
        pwm.start()
        while True:
            v = input('enter new voltage or q to quit: ')
            if v.lower()[0] == 'q':
                print('quitting.')
                break
            pwm.set_voltage(float(v))
        pwm.stop()

