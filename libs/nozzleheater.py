import pyvisa

# VISAID = 'nozzleheaterethernet'
VISAID = 'nozzleheater'

readterm = '\n'
writeterm = '\r\n'

class NozzleHeaterHandler:
    def __init__(self,visaid=VISAID):
        self.visaid = visaid

    def __enter__(self):
        self.handle = open_nozzle_heater(self.visaid)        
        self.handle.read_termination = readterm
        self.handle.write_termination = writeterm
        self.handle.baud_rate = 9600
        return self.handle

    def __exit__(self,*args):
        close_nozzle_heater(self.handle)

def open_nozzle_heater(visaid=VISAID):
    return pyvisa.ResourceManager().open_resource(visaid)

def close_nozzle_heater(handle):
    handle.close()

def get_description(handle):
    return handle.query('Description')

# celsius
def get_output(handle):
    return [float(x) for x in handle.query('getOutput').strip().split(', ')]

def get_output_names(handle):
    return handle.query('getOutputNames').strip()

# celsius
def get_nozzle_setpoint(handle):
    return float(handle.query('"Nz heating.PID.Setpoint?"'))

def set_nozzle_setpoint(handle,setpoint):
    return handle.write('"Nz heating.PID.Setpoint"={}'.format(str(setpoint)))

def send_popup(handle,message):
    return handle.write('popup "{}"'.format(message))

if __name__ == '__main__':
    with NozzleHeaterHandler() as nhh:
        print(send_popup(nhh,'hello, whirled'))
        print(get_description(nhh))
        print(get_output(nhh))
        print(get_output_names(nhh))
        print(get_nozzle_setpoint(nhh))
        set_nozzle_setpoint(nhh,30.0)
        print(get_nozzle_setpoint(nhh))

    
