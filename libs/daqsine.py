import daqmx, numpy as np

class DaqSine(daqmx.TaskHandler):
    def __init__(self,channel,samplingrate,responsetime,frequency,amplitude):
        super().__init__([channel])
        self.channel = channel
        self.samplingrate = samplingrate
        self.responsetime = responsetime
        self.frequencyo = frequency
        self.buffersize = int(self.samplingrate*self.responsetime)
        self.transsamps = self.buffersize
        self.set_frequency(frequency)
        self.amplitudeo = 0.0
        self.set_amplitude(amplitude)
        self.phase = 0.0        
        daqmx.cfg_samp_clk_timing(
            self.task,
            self.samplingrate,
            daqmx.CONT_SAMPS,
            self.buffersize
        )
        daqmx.set_regeneration_mode(self.task,False)
        self.written_samples = 0
        self._generate_samples(self.buffersize)

    def set_frequency(self,frequency):
        self.frequency = frequency
        self.dfrequency = (self.frequency - self.frequencyo)/self.transsamps
        self.nfrequency = self.transsamps        

    def set_amplitude(self,amplitude):        
        self.amplitude = amplitude
        self.damplitude = (self.amplitude - self.amplitudeo)/self.transsamps
        self.namplitude = self.transsamps

    def generate_samples(self):
        return self._generate_samples(self.get_available_samples())

    def _generate_samples(self,nsamps):        
        samps = []        
        while nsamps:            
            if self.nfrequency:
                self.frequencyo += self.dfrequency
                frequency = self.frequencyo
                self.nfrequency -= 1
            else:
                frequency = self.frequency
            if self.namplitude:
                self.amplitudeo += self.damplitude
                amplitude = self.amplitudeo
                self.namplitude -= 1
            else:
                amplitude = self.amplitude
            self.phase += 2 * np.pi * frequency / self.samplingrate
            while self.phase > 2 * np.pi:
                self.phase -= 2 * np.pi
            samp = amplitude * np.sin(self.phase)
            samps.append(samp)            
            nsamps -= 1
            self.written_samples += 1                    
        daqmx.write_to_buff(self.task,samps)                

    def __enter__(self):
        return self
    
    def start(self):
        daqmx.start_task(self.task)

    def stop(self):
        daqmx.stop_task(self.task)

    def get_available_samples(self):
        return daqmx.get_samps_generated(self.task) - self.written_samples + self.buffersize
    
    def get_buffer_size(self):
        return self.buffersize
    
if __name__ == '__main__':
    import time, msvcrt
    deltat = 20.0
    epsilont = 0.25
    
    with DaqSine('sine wave generator',10000,1.0,100,1) as sh:
        bufsize = sh.get_buffer_size()
        width = int(np.log10(bufsize)+3)
        sh.start()        
        command = ''
        to = time.time()
        while True: 
            sh.generate_samples() 
            # t = time.time()   
            # if t - to > epsilont:
            #     to = t
            #     samps = sh.get_available_samples()
            #     print(
            #         'buffer: {} samps'.format(
            #             ' / '.join(
            #                 str(s).rjust(width)
            #                 for s in 
            #                 (
            #                     sh.get_available_samples(),
            #                     bufsize
            #                 )
            #             )
            #         )
            #     )
            #     if 2 * samps > bufsize:
            #         sh.generate_samples()        
            while msvcrt.kbhit():
                key = msvcrt.getche().decode('ASCII')
                # print('key hit:','ord',str(ord(key)).rjust(3),'|','command:',command)
                if key != '\r':                    
                    command += key
                    continue   
                msvcrt.putch('\n'.encode())
                if not command: continue
                commandkey, *commandval = command.lower()
                command = ''                
                if commandkey == 'q':
                    sh.stop()
                    print('quitting.')
                    exit(0)                             
                if commandkey == 'b':
                    print(
                        'buffer: {} samps'.format(
                            ' / '.join(
                                str(s).rjust(width)
                                for s in 
                                (
                                    sh.get_available_samples(),
                                    bufsize
                                )
                            )
                        )
                    )
                    continue
                if not commandval:
                    print('must specify value')
                    continue
                commandval = ''.join(commandval).strip()
                if not commandval:
                    print('must specify value')
                    continue
                try:
                    commandval = float(''.join(commandval))
                    if commandkey == 'f':
                        sh.set_frequency(commandval)
                        continue
                    elif commandkey == 'a':
                        sh.set_amplitude(commandval)
                        continue                                
                except ValueError:
                    print('invalid value')
                    continue                            
                print('unknown command')