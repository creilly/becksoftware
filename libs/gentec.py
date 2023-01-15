import pyvisa

VISA_ID = 'gentec'
read_term = '\n'

class GentecHandler:
    def __init__(self,visa_id=VISA_ID):
        self.pm = pm = open_pm(visa_id)
        pm.baud_rate = 115200
        if visa_id != VISA_ID:
            pm.write_termination = '\r'
        pm.read_termination = read_term # '\r'
        
    def __enter__(self):
        return self.pm
    def __exit__(self,*args):
        close_pm(self.pm)

def open_pm(visa_id=VISA_ID):
    return pyvisa.ResourceManager().open_resource(visa_id)

def close_pm(pm):
    pm.close()

def send_command(pm,command,response=True):
    return getattr(pm,{True:'query',False:'write'}[response])('*{}'.format(command))

def get_version(pm):
    return send_command(pm,'VER')

def get_power(pm):
    return float(send_command(pm,'CVU').strip().split(' ')[-1])

def start_stream(pm):
    pm.write('*CAU')

def stop_stream(pm):
    pm.write('*CSU')
    pm.timeout = 100
    try:
        sum = 0
        n = 0
        while True:
            sum += float(pm.read().strip())
            n += 1
    except pyvisa.errors.VisaIOError:        
        return sum / n if n else None

def set_autoscale(pm,autoscale):
    return send_command(pm,'SAS {:d}'.format(int(autoscale)),False)

RANGE_1W = 24
def set_range(pm,range):
    return send_command(pm,'SCS {:d}'.format(range),False)

if __name__ == '__main__':
    from time import sleep
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('-v','--visa-id',default=VISA_ID)
    try:
        print('gentec power monitor. press ctrl-c to quit.')
        with GentecHandler() as pm:
            for _ in range(2):
                start_stream(pm)
                sleep(2.0)
                print('power:',stop_stream(pm))            
            print(get_power(pm))
            # while True:
            #     print(get_power(pm))
            #     sleep(0.001)
    except KeyboardInterrupt:
        print('interrupt received quitting...')
