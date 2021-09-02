from ctypes import *
from daqmx import *
from time import sleep

def load_pulse_gen(channel):
    taskhandle = create_task()
    add_global_channel(taskhandle, channel)
    set_samp_timing_type(taskhandle, IMPLICIT_TIMING)
    return taskhandle

def close_pulse_gen(handle):
    clear_task(handle)

def step_motor(pulse_gen,steps):
    set_samples(pulse_gen,steps)
    start_task(pulse_gen)
    task_wait(pulse_gen)
    stop_task(pulse_gen)
        
FORWARDS = True
BACKWARDS = False
slope = 10000 / 0.20825 # steps per inch
def move_sample(pulse_gen,dir_line,displacement):
    steps = int(slope*abs(displacement))
    if not steps:
        return
    write_line(
        dir_line,
        FORWARDS if displacement > 0 else BACKWARDS        
    )
    step_motor(pulse_gen,steps)

def _move_sample(displacement):
    dirline = load_line('auger motor x dir')
    pulsegen = load_pulse_gen('auger motor x clock')
    move_sample(pulsegen,dirline,displacement)
    close_line(dirline)
    close_pulse_gen(pulsegen)
    
if __name__ == '__main__':
    _move_sample(+0.050)
    sleep(1.0)
    _move_sample(-0.075)
    _move_sample(+0.025)
    # dirline = load_line('auger stepper motor direction')
    # stepline = load_line('auger stepper motor step')
    # steps = 100
    # delay = 0.02
    # for direction in (True,False):
    #     write_line(dirline,direction)
    #     step = 0
    #     while step < steps:        
    #         step += 1
    #         print(direction,step)
    #         write_line(stepline,False)
    #         sleep(delay)
    #         write_line(stepline,True)
    #         sleep(delay)
    # for line in (dirline,stepline):
    #     close_line(line)
