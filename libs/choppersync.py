import maxon, chopper, daqmx, numpy as np, time

c_phase = 0.00010 # rpm per (degree per update)
c_freq = 0.10000 # rpm per (degree per update)
cbdt = 0.25 # seconds
stat_samples = 100
mup_thresh = 2.0 # degrees
sigmap_thresh = 2.0 # degrees

phase_setpoint = 180. # degrees

dphimax = 160 # degrees
dvmax = 10. # rpm

def time_to_phase(t,f):
    return t * f * 360

def phase_to_time(p,f):
    return p / f / 360

class ChopperSyncException(Exception):
    pass

class ChopperSyncStateException(ChopperSyncException):
    def __init__(self,state,states):
        super().__init__('current state [{}] not in valid states ({}) for this method'.format(state,', '.join(states)))

def state_filter(*states):
    def g(f):
        def _f(self,*args,**kwargs):
            if self.state not in states:
                raise ChopperSyncStateException(self.state,states)
            return f(self,*args,**kwargs)
        return _f
    return g

class ChopperSyncHandler:
    STOPPED, STARTING, STARTED, LOCKING, LOCKED, STOPPING = 'stopped', 'starting', 'started', 'locking', 'locked', 'stopping'
    def __init__(self,maxon_handler,frequency,verbose=True):
        self.mh = maxon_handler
        self.vo = frequency * 60 / 2
        self.to = phase_setpoint / 360 / frequency
        self.state = self.STOPPED
        self.units = maxon.get_velocity_units(self.mh)
        self.verbose = verbose

    def get_state(self):
        return self.state

    def __enter__(self):
        self._ct = daqmx.TaskHandler('jitter task',global_task=True)
        self.ct = self._ct.__enter__()
        self.samps_per_channel = daqmx.get_samps_per_channel(self.ct)
        return self

    def __exit__(self,*args):
        chopper.set_blocking(self.mh,True)
        self._ct.__exit__(*args)

    @state_filter(STOPPED)
    def start(self):
        yield from self._move(self.vo,self.STARTING,self.STARTED)

    @state_filter(STARTED)
    def lock(self):
        daqmx.start_task(self.ct)
        maxon.set_operation_mode(self.mh,maxon.M_VELOCITY)
        self.v = self.vo
        self.erroro = None # degress
        self.stat_sample = 0
        self.mup = self.mup2 = None # degrees, degrees ** 2
        self.state = self.LOCKING
        self.tcb = time.time() # seconds
        self.triggered = False

    def get_average(self):
        return self.mup
    
    def get_std(self):
        return np.sqrt(self.mup2 - self.mup**2)

    @state_filter(LOCKING,LOCKED)
    def update(self):
        data, samps = daqmx.read_counter_f64(self.ct,self.samps_per_channel)            
        if not samps: return
        errors = time_to_phase(np.average(np.ctypeslib.as_array(data)[:samps] - self.to))
        if self.erroro is None:
            self.erroro = self.errors[0]
        dv = c_phase * errors.sum() + c_freq * ( errors[-1] - self.erroro )
        self.erroro = errors[-1]
        for error in errors:
            if self.mup is None:
                self.mup = error
            if self.mup2 is None:
                self.mup2 = error**2
            self.mup = self.mup * (stat_samples-1) / stat_samples + error / stat_samples
            self.mup2 = self.mup2**2 * (stat_samples-1) / stat_samples + error**2 / stat_samples
            self.stat_sample += 1
            self.state = (
                self.LOCKED 
                if
                self.stat_sample > self.stat_samples and abs(self.get_average()) < mup_thresh and self.get_std() < sigmap_thresh
                else 
                self.LOCKING
            )                
        if self.verbose and time.time() - self.tcb > cbdt:    
            self.tcb = time.time()
            print(
                'vel:','{:.3f} rpm'.format(self.v).rjust(15),',',
                'err:',(
                    '{:.2f} +- {:.2f} degs'.format(self.get_average(),self.get_std())
                    if self.get_average() is not None else
                    'NA'
                ).rjust(24),',',
                'samps:',samps,',',
                self.get_state()
            )
        if not self.triggered:
            if abs(self.get_average() < dphimax):
                if self.verbose:
                    print('locking triggered. servo loop closed.')
                self.triggered = True
            else:
                if self.verbose and time.time() - self.tcb > cbdt:    
                    self.tcb = time.time()
                    print('bumping velocity to get away from edge...')                    
                dv = (+1 if self.get_average() < 0 else -1) * 0.001 # rpm
        if self.triggered:
            self.v += dv
        if abs(self.v-self.vo) > dvmax:
            raise ChopperSyncException('max velocity range exceeded.')        
        maxon.set_velocity(self.mh,self.v,self.units)

    @state_filter(LOCKING,LOCKED)
    def unlock(self):
        daqmx.stop_task(self.ct)
        self.state = self.STARTED

    def _move(self,v,prestate,poststate):
        self.state = prestate
        chopper.start_spin(self.mh,v)
        cb = chopper._velcb(v,self.units)
        t = time.time()
        while not maxon.get_movement_state(self.mh):
            if self.verbose:
                if time.time() - t > cbdt:
                    cb(self.mh)
                    t = time.time()
            yield
        print('target reached.')
        self.state = poststate

    @state_filter(STARTING,STARTED)
    def stop(self):
        self._move(0.0,self.STOPPING,self.STOPPED)

def get_frequency():
    with daqmx.TaskHandler('pll freq task',global_task=True) as ct:
        daqmx.start_task(ct)
        frequency = daqmx.read_counter_f64_scalar(ct)
        daqmx.stop_task(ct)
        return frequency
    
if __name__ == '__main__':
    import msvcrt, beckasync
    frequency = get_frequency()
    print('freq: {:.2f} Hz'.format(frequency))
    with maxon.MaxonHandler() as mh:
        with ChopperSyncHandler(mh,frequency) as csh:
            beckasync.unwind_generator(csh.start())
            csh.lock()
            while True:
                if msvcrt.kbhit():
                    if msvcrt.getwch() == 'q':
                        print('quit command received')                        
                        csh.unlock()
                        beckasync.unwind_generator(csh.stop())
                        exit(0)
                csh.update()