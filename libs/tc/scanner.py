import numpy as np, daqmx

class Scanner:
    buffer_size = 10 # in scans
    decimation = 4
    UP = 'up'
    DOWN = 'down'
    INDEX = 'index'
    MARGNINED = 'margined'
    DECIMATED = 'decimated'
    def __init__(
        self,
        piezo_task,detector_task,trigger_task,
        sampling_rate,scan_period,
        scan_amplitude,curve_fraction,
        margin, ext_trigger = False        
    ):
        self.aot = piezo_task
        self.ait = detector_task
        self.cot = trigger_task
        self.sampling_rate = sampling_rate
        self.deltat = scan_period
        self.deltav = scan_amplitude
        self.epsilon = curve_fraction
        self.ext_trigger = ext_trigger
        self.margin_samps = int(scan_period * margin * sampling_rate / 4)
        self.n_chans = daqmx.get_num_chans(self.ait)
        self.channels = daqmx.get_task_channels(self.ait)        
        self.data_array = np.empty((0,self.n_chans))

        self.scanning = False
        self.reset_scanning()
        
        self.configure_tasks()  

    def reset_scanning(self):
        self.scans = {
            direction:None
            for direction in (self.UP,self.DOWN)
        }
        self.direction = self.UP        

    def decimate(self,array):
        return np.average(
            array[:(len(array)//self.decimation)*self.decimation].reshape(
                (-1,self.decimation)
            ), axis = 1
        )
    
    def configure_tasks(self):
        self.create_ramp()
        if not self.ext_trigger:
            # feed dummy reference to trigger input   
            daqmx.cfg_implicit_timing(self.cot,daqmx.CONT_SAMPS,1)
            daqmx.set_co_term(self.cot,daqmx.get_dig_edge_start_trig_src(self.aot))
            daqmx.start_task(self.cot)
        for task in (self.aot,self.ait):
            daqmx.set_samp_clk_rate(task,self.sampling_rate)
            daqmx.set_samples(
                task, (
                    self.buffer_size if task == self.ait else 1
                ) * len(self.ramp)
            )
        daqmx.set_retriggerable(self.aot,True)
        daqmx.write_to_buff(self.aot,self.ramp)

    def create_ramp(self):    
        halftime = self.deltat / 2
        delta = np.sqrt(2*self.epsilon)
        vpp = self.deltav / halftime**2 * (delta + 1 / delta)**2
        tau = np.sqrt(self.deltav/vpp)
        parabolasamps = int(delta*tau*self.sampling_rate)
        linesamps = int((1/delta-delta)*tau*self.sampling_rate)    
        upramp = np.cumsum(
            np.cumsum(
                np.hstack(
                    (
                        +vpp * np.ones(parabolasamps),
                        np.zeros(linesamps),
                        -vpp * np.ones(parabolasamps),
                    )
                )
            ) / self.sampling_rate
        ) / self.sampling_rate
        downramp = upramp[::-1]    
        ramp = np.hstack((upramp,downramp))
        self.ramp = ramp
        self.parabolasamps = parabolasamps
        self.scan_samps = len(upramp)
        self.margined_ramps = {
            self.UP:ramp[:self.scan_samps][self.margin_samps:-self.margin_samps] - self.deltav / 2,
            self.DOWN:ramp[self.scan_samps:][self.margin_samps:-self.margin_samps] - self.deltav / 2
        }      
        self.decimated_ramps = {
            direction:self.decimate(array)
            for direction, array in self.margined_ramps.items()
        }

    def get_scanning(self):
        return self.scanning

    def set_scanning(self,scanning):
        if scanning != self.scanning:
            for task in (self.ait,self.aot):                
                if scanning:     
                    self.direction = self.UP                     
                    daqmx.start_task(task)
                else:                    
                    daqmx.stop_task(task)                    
        self.scanning = scanning

    def read(self,samples=daqmx.DAQmx_Val_Auto):
        newdata = np.array(
            daqmx.read_buff(
                self.ait, samples, self.n_chans, 
                timeout = None if samples < 0 else 2.0
            )
        ).transpose()          
        self.data_array = np.concatenate(
            (
                self.data_array,
                newdata
            )
        )  
        direction = self.direction      
        if len(self.data_array) >= self.scan_samps:
            scan_array = self.data_array[:self.scan_samps]            
            self.data_array = self.data_array[self.scan_samps:] 
            margined_arrays = scan_array[self.margin_samps:-self.margin_samps].transpose()
            margd = {}
            decid = {}
            for channel, margined_array in zip(
                self.channels,margined_arrays
            ):
                margd[channel] = margined_array
                decid[channel] = self.decimate(margined_array)
            scano = self.scans[direction]
            if scano is None:
                index = 1
            else:
                index = scano[self.INDEX] + 1
            scan = {
                self.INDEX:index,
                self.MARGNINED:margd,
                self.DECIMATED:decid
            }
            self.scans[direction] = scan            
            self.direction = {
                self.UP:self.DOWN, self.DOWN:self.UP
            }[direction]
        else:
            scan = None            
        return direction, scan