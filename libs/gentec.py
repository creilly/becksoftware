import pyvisa

VISA_ID = 'gentec'
read_term = '\n'

class GentecHandler:
    def __init__(self,visa_id=VISA_ID):
        self.pm = pm = open_pm(visa_id)
        pm.baud_rate = 115200
        # pm.write_termination = '\r'
        pm.read_termination = read_term # '\r'
        
    def __enter__(self):
        return self.pm
    def __exit__(self,*args):
        close_pm(self.pm)

def open_pm(visa_id=VISA_ID):
    return pyvisa.ResourceManager().open_resource(visa_id)

def close_pm(pm):
    pm.close()

def send_command(pm,command):
    return pm.query('*{}'.format(command))

def get_version(pm):
    return send_command(pm,'VER')

def get_power(pm):
    return float(send_command(pm,'CVU').strip().split(' ')[-1])

if __name__ == '__main__':
    from time import sleep
    try:
        print('gentec power monitor. press ctrl-c to quit.')
        with GentecHandler() as pm:
            while True:
                print(get_power(pm))
                sleep(0.001)
    except KeyboardInterrupt:
        print('interrupt received quitting...')
