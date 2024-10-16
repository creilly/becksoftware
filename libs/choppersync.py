import maxon, chopper, daqmx, numpy as np, time

c_phase = 0.00015 # rpm per (degree per update)
c_freq = 0.10000 # rpm per (degree per update)
cbdt = 0.25 # seconds
stat_samples = 500
mup_thresh = 2.0 # degrees
sigmap_thresh = 5.0 # degrees

phase_setpoint = 180. # degrees

dphimax = 50 # degrees
dvmax = 10. # rpm
epsilonvmax = 3 # rpm

def time_to_phase(t,f):
    return t * f * 360

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
        self.fo = frequency
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
    
    def block(self):
        maxon.set_operation_mode(self.mh,maxon.M_PROFILE_VELOCITY)
        chopper.start_halt(self.mh)
        chopper.wait_halt(self.mh,1.0)
        chopper.start_home(self.mh)
        chopper.wait_home(self.mh,1.0,lambda mh: print('homing...'))
        chopper.set_blocking(self.mh,True)
        chopper.wait_movement(self.mh,1.0,lambda mh: print('moving to blocked position...'))
        print('chopper blocking.')

    def __exit__(self,*args):
        self._ct.__exit__(*args)
        self.block()

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
        self.errors = np.empty(0)   

    def get_average(self):
        return self.mup
    
    def get_std(self):
        return np.sqrt(self.mup2 - self.mup**2)
    
    def get_errors(self):
        data, samps = daqmx.read_counter_f64(self.ct,self.samps_per_channel)            
        return time_to_phase(np.ctypeslib.as_array(data)[:samps] - self.to,self.fo)
    
    @state_filter(LOCKING,LOCKED)
    def update(self):        
        errors = self.get_errors()
        samps = len(errors)
        if samps == 0: return
        self.errors = np.hstack([self.errors,errors])
        errors = self.errors[:2 * (len(self.errors)//2)]
        self.errors = self.errors[2 * (len(self.errors)//2):]    
        if len(errors) == 0: return    
        errors = np.average(errors.reshape(len(errors)//2,2),1)
        samps = len(errors)
        if self.erroro is None:
            self.erroro = errors[0]
        # phase wrap
        for i in range(len(errors)):
            while abs(errors[i]-self.erroro) > 180:
                errors[i] += (+1 if errors[i] < self.erroro else -1) * 360
        dv = c_phase * errors.sum() + c_freq * ( errors[-1] - self.erroro )        
        self.erroro = errors[-1]
        for error in errors:
            if self.mup is None:
                self.mup = error
            if self.mup2 is None:
                self.mup2 = error**2
            self.mup = self.mup * (stat_samples-1) / stat_samples + error / stat_samples
            self.mup2 = self.mup2 * (stat_samples-1) / stat_samples + error**2 / stat_samples
            self.stat_sample += 1
            self.state = (
                self.LOCKED 
                if
                self.stat_sample > stat_samples and 
                abs(self.get_average()) < mup_thresh and 
                self.get_std() < sigmap_thresh
                else 
                self.LOCKING
            )
        triggered_update = False               
        if self.verbose and time.time() - self.tcb > cbdt:    
            triggered_update = True
            self.tcb = time.time()
            print(
                'vel:','{:.3f} rpm'.format(self.v).rjust(15),',',
                'err:',(
                    '{} +- {} degs'.format(*['{:.2f}'.format(phase).rjust(10) for phase in (self.get_average(),self.get_std())])
                    if self.get_average() is not None else
                    'NA'
                ),',',
                'samps:',samps,',',
                self.get_state()
            )
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
        print('target reached. set vel {:.3f} rpm'.format(maxon.get_velocity_set(self.mh,self.units)))
        self.state = poststate

    @state_filter(STARTING,STARTED)
    def stop(self):
        yield from self._move(0.0,self.STOPPING,self.STOPPED)

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
                        csh.block()
                        exit(0)
                csh.update()