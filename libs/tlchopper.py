import pyvisa

VISA_ID = 'thorlabs-chopper'
BAUD_RATE = 115200

termseq = '\r> '
termlen = len(termseq)

writeterm = '\r'

class TLChopperHandler:
    def __init__(self,visa_id=VISA_ID):
        self.pah = open_tlc(visa_id)

    def __enter__(self):
        return self.pah

    def __exit__(self,*args):
        close_tlc(self.pah)

def open_tlc(visa_id):
    tlc = pyvisa.ResourceManager().open_resource(visa_id)
    tlc.write_termination = None
    tlc.baud_rate = BAUD_RATE
    tlc.timeout = 100 # milliseconds
    return tlc

def close_tlc(tlc):
    tlc.close()

def read_response(tlc):
    response = ''
    while True:
        response += tlc.read_bytes(1).decode()
        if response[-termlen:] == termseq:
            break
    return response[:-termlen]

def write_command(tlc,command):
    tlc.write(command + writeterm)

def parse_response(response):
    return '\n'.join(response.split('\r')[1:])

def send_command(tlc,command):
    write_command(tlc,command)
    return parse_response(read_response(tlc))

def get_id(tlc):
    return send_command(tlc,'id?')

def get_phase(tlc):
    return int(send_command(tlc,'phase?'))

def set_phase(tlc,phase):
    return send_command(tlc,'phase={:d}'.format(phase))

TARGET, ACTUAL = 0, 1
def set_reference_output(tlc,reference_output):
    return send_command(tlc,'output={:d}'.format(reference_output))

def get_command_list(tlc):
    return send_command(tlc,'?')

def get_locked(tlc):
    return bool(send_command(tlc,'locked?'))

if __name__ == '__main__':
    with TLChopperHandler() as tlch:
        print('locked?',get_locked(tlch))