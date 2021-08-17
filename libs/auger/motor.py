from ctypes import *
from .daqmx import *
from time import sleep

def get_exponent(taskhandle):
    strbuf = create_string_buffer(bufsize)
    daqmx(
        dll.DAQmxGetPhysicalChanName,
        taskhandle,
        None,
        strbuf,
        bufsize
    )
    return int(
        strbuf.value.decode('utf8').split(', ')[0].split('/')[-1].split('line')[-1]
    )

def load_line(channel):
    taskhandle = create_task()
    add_global_channel(taskhandle,channel)
    exp = get_exponent(taskhandle)
    return (taskhandle,exp)

def close_line(line):
    taskhandle, exp = line
    clear_task(taskhandle)

def write_line(line,state):
    handle, exp = line
    daqmx(
        dll.DAQmxWriteDigitalScalarU32,
        handle,
        True,
        -1,
        int(state) * 2 ** exp,
        None
    )

def step_motor(line,delay,steps):
    for step in range(steps):
        write_line(line,False)
        sleep(delay)
        write_line(line,True)
        sleep(delay)
        
FORWARDS = False
BACKWARDS = True
slope = 10000 / 0.20825 # steps per inch
def move_sample(step_line,dir_line,displacement,delay):
    write_line(
        dir_line,
        FORWARDS if displacement > 0 else BACKWARDS        
    )
    sleep(delay)
    step_motor(step_line,delay,int(slope*abs(displacement)))

def _move_sample(displacement,delay):
    dirline = load_line('auger stepper motor direction')
    stepline = load_line('auger stepper motor step')
    move_sample(stepline,dirline,displacement,delay)
    for line in (dirline,stepline): close_line(line)
    
if __name__ == '__main__':
    dirline = load_line('auger stepper motor direction')
    stepline = load_line('auger stepper motor step')
    steps = 100
    delay = 0.02
    for direction in (True,False):
        write_line(dirline,direction)
        step = 0
        while step < steps:        
            step += 1
            print(direction,step)
            write_line(stepline,False)
            sleep(delay)
            write_line(stepline,True)
            sleep(delay)
    for line in (dirline,stepline):
        close_line(line)
