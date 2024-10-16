import beckhttpserver as bhs, daqmx, struct, base64, topo, numpy as np
from tc import scanner, fitter, locker
import tc

def encode_scan(scan):
    return base64.b64encode(
        struct.pack(
            '{:d}f'.format(len(scan)),
            *scan
        )
    ).decode()

directions = (
    scanner.Scanner.UP, scanner.Scanner.DOWN
)

laserd = {
    scanner.Scanner.UP:locker.ARGOS,
    scanner.Scanner.DOWN:locker.TOPO,
}

def encode_scan(scan):    
    return base64.b64encode(
        struct.pack(
            '{:d}f'.format(len(scan)),
            *scan
        )
    ).decode()

SCAN = 'scan'
FIT = 'fit'
HENE = 'hene'
IR = 'ir'
class TransferCavityApp(bhs.BeckApp):    
    history = 1000
    def __init__(self,aot,ait,cot,modfreq):
        self.freqmod = modfreq is not None
        self.channels = {
            name:key
            for key, name in zip(
                (HENE,IR),daqmx.get_task_channels(ait)
            )
        }
        self.scanner = s = scanner.Scanner(
            aot,ait,cot,
            tc.samplingrate,tc.deltat,tc.deltav,tc.epsilon,tc.buffer,
            tc.freqmod is not None
        )
        self.fitters = {
            d:fitter.Fitter(
                s.margined_ramps[d],
                modfreq if laserd[d] == locker.TOPO else None
            ) for d in directions
        }
        # ic = topo.AsyncInstructionClient()        
        self.lockers = {
            d:locker.Locker(
                locker.PiezoControl(
                    laser,topo.AsyncInstructionClient()
                ),
                locker.dfdvsd[laser],
                locker.dampingd[laser]
            ) for d, laser in [
                (d,laserd[d])
                for d in directions
            ]
        }        
        self.fitting = {
            d:False for d in directions
        }
        self.locking = {
            d:False for d in directions
        }
        self.frequencies = {
            d:(
                -1,
                [None]*TransferCavityApp.history
            ) for d in directions            
        }
        self.reset_scans()

    def reset_scans(self):
        self.scans = {
            d:None for d in directions
        }

    def loop(self):        
        if self.get_scanning():
            d, data = self.scanner.read(self.scanner.scan_samps)
            if data is not None:
                self.scans[d] = data                
                f = None
                if self.fitting[d]:
                    Vhenes, Virs = [
                        data[self.scanner.MARGNINED][channel]
                        for channel in self.scanner.channels
                    ]
                    success = self.fitters[d].update_hene(Vhenes)
                    if success:
                        success = self.fitters[d].update_ir(Virs)                    
                        if success:
                            ffit = self.fitters[d].f
                            if self.locking[d]:
                                self.lockers[d].update(ffit)
                            else:
                                self.lockers[d].control.check_mc()
                            f = ffit - self.lockers[d].f_offset                
                index, farray = self.frequencies[d]
                index += 1
                farray.pop(0)
                farray.append(f)
                self.frequencies[d] = (index,farray)

    @bhs.command('get lock output')
    def get_lock_output(self,direction):
        return self.lockers[direction].get_control()

    @bhs.command('get setpoint')
    def get_setpoint(self,direction):
        return self.lockers[direction].get_setpoint()

    @bhs.command('set setpoint')
    def set_setpoint(self,direction,setpoint):
        self.lockers[direction].set_setpoint(setpoint)

    @bhs.command('get locking')
    def get_locking(self,direction):
        return self.locking[direction]

    @bhs.command('set locking')
    def set_locking(self,direction,locking):        
        self.locking[direction] = locking

    @bhs.command('zero offset')
    def zero_offset(self,direction):
        f = self.fitters[direction].f
        if f is None:
            raise bhs.BeckError('cannot offset zero: no measured frequency')
        self.lockers[direction].set_offset(
            self.fitters[direction].f
        )

    @bhs.command('get frequency')
    def get_frequency(self,direction):
        f = self.fitters[direction].f
        if f is None: return None
        return f - self.lockers[direction].get_offset()
    
    @bhs.command('get frequencies')
    def get_frequencies(self,direction,index):
        indexp, farray = self.frequencies[direction]
        samples = indexp - index
        if samples < 1: return []
        return farray[-samples:]
    
    @bhs.command('get frequencies index')
    def get_frequencies_index(self,direction):
        return self.frequencies[direction][0]

    @bhs.command('get scanning')
    def get_scanning(self):        
        return self.scanner.get_scanning()

    @bhs.command('set scanning')
    def set_scanning(self,scanning):
        if scanning == self.scanner.scanning: return
        if scanning:
            self.reset_scans()            
            for fitter in self.fitters.values():
                fitter.reset()                
            for locker in self.lockers.values():
                locker.reset()
        self.scanner.set_scanning(scanning)        

    @bhs.command('get scan index')
    def get_scan_index(self,direction):
        return self.scans[direction][scanner.Scanner.INDEX]

    @bhs.command('get scan')
    def get_scan(self,direction,decimated):
        scan = self.scans[direction]    
        if scan is None:
            return None    
        index = scan[scanner.Scanner.INDEX]        
        return [
            index,{
                self.channels[channel]:{
                    SCAN:encode_scan(channel_data),
                    FIT:[
                        getattr(self.fitters[direction],attr)
                        for attr in {
                            HENE:('henecalib','etaparams'),
                            IR:('ircalib','f')
                        }[self.channels[channel]]
                    ]
                }
                for channel, channel_data in scan[
                    {
                        True:scanner.Scanner.DECIMATED,
                        False:scanner.Scanner.MARGNINED
                    }[decimated]
                ].items()
            }
        ]        

    @bhs.command('get x')
    def get_x(self,direction,decimated):
        return encode_scan(
            {
                True:self.scanner.decimated_ramps,
                False:self.scanner.margined_ramps
            }[decimated][direction]
        )

    @bhs.command('get fitting')
    def get_fitting(self,direction):
        return self.fitting[direction]

    @bhs.command('set fitting')
    def set_fitting(self,direction,fitting):        
        if fitting:
            self.fitters[direction].reset()
        self.fitting[direction] = fitting   

    @bhs.command('get fit parameters') 
    def get_fit_parameters(self,direction):
        pass

    @bhs.command('get frequency modulation mode')
    def get_frequency_modulation_mode(self):
        return self.freqmod

if __name__ == '__main__':
    import os
    
    with (
        daqmx.TaskHandler('transfer cavity piezo task',global_task=True) as aot,
        daqmx.TaskHandler('transfer cavity detector task',global_task=True) as ait,
        daqmx.TaskHandler(['transfer cavity sync']) as cot, 
        daqmx.TaskHandler([]) as fmt, # freqmod divider
        daqmx.TaskHandler('transfer cavity frequency task',global_task=True) as cit,
    ):
        if tc.freqmod is not None:
            print('frequency modulation enabled')
            from matplotlib import pyplot as plt
            print('measuring modulation frequency...')            
            samps = daqmx.get_samps_per_channel(cit)                        
            daqmx.start_task(cit)            
            modfreqs, samps_acquired = daqmx.read_counter_f64(
                cit,samps,True,
                timeout = 2 * tc.modfreqo * samps
            )
            daqmx.stop_task(cit)            
            modfreq = np.average(modfreqs)
            dmodfreq = np.std(modfreqs)
            print(
                'measured frequency (Hz) |', ' , '.join(
                    '{}: {:.8f}'.format(label,f)
                    for label, f in (('avg',modfreq),('std',dmodfreq))
                )
            )
            cycles = int(modfreq*tc.deltat) + 1
            high_cycles = cycles // 2
            low_cycles = cycles - high_cycles
            print(
                'trigger division (modulation cycles) |',
                high_cycles,'high',',',
                low_cycles,'low'
            )
            t_delay = 1/2 * (
                tc.deltat + 
                (low_cycles-high_cycles)/(low_cycles+high_cycles)/modfreq
            )
            print(
                'optimal srs chopper delay setpoint:',round(1e3*t_delay,3),'milliseconds'
            )            
            daqmx.create_co_ticks_channel(
                fmt,daqmx.get_physical_channel(cot),high_cycles,low_cycles,
                daqmx.get_ci_freq_term(cit)
            )
            daqmx.cfg_samp_clk_timing(
                fmt,modfreq,daqmx.CONT_SAMPS,100,
                daqmx.get_ci_freq_term(cit)
            )
            daqmx.write_ticks(
                fmt,[[high_cycles,low_cycles]]*100
            )
            daqmx.set_co_term(fmt,daqmx.get_dig_edge_start_trig_src(aot))            
            daqmx.start_task(fmt)
        else:
            print('frequency modulation disabled')
            modfreq = None            
        bhs.run_beck_server(
            tc.PORT,
            os.path.dirname(__file__),
            TransferCavityApp,
            aot,ait,cot,modfreq,
            _debug=False
        )