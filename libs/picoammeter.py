import pyvisa as visa
import re

VISA_ID = 'picoammeter'

termseq = '\r\n'

BAUDRATE = 57600

chunksize = 16

class PicoammeterHandler:
    def __init__(self,visa_id=VISA_ID):
        self.pah = open_pa(visa_id)

    def __enter__(self):
        return self.pah

    def __exit__(self,*args):
        close_pa(self.pah)

def open_pa(visa_id=VISA_ID):
    pah = visa.ResourceManager().open_resource(visa_id)
    pah.baud_rate = BAUDRATE    
    pah.read_termination = pah.write_termination = termseq
    pah.timeout = 50
    set_interval(pah,0)
    return pah

def close_pa(pah):
    pah.close()

def send_command(pah,command,data = ''):
    pah.write(
        '&{}{}'.format(command,data)
    )

# set to 0 to disable interval
# response is set interval in milliseconds
def set_interval(pah,interval):
    return int(query_pa(pah,'I','{:04d}'.format(interval)).split('=')[1][:4])

def get_match(command,response):
    match = re.compile(
        '^&{}(.*)'.format(command)
    ).match(
        response
    )
    if match is None:
        return None
    return match.groups()[0]

def parse_response(pah,command):
    response = None
    tail = ''
    while True:
        try:
            chunk = pah.read_bytes(chunksize,chunksize,True).decode('utf8')
            tail += chunk
            if termseq in tail:
                head, tail = tail.split(termseq,1)
                response = get_match(command,head)
        except visa.errors.VisaIOError:
            if response is None:
                continue
            return response

def query_pa(pah,command,data=''):
    send_command(pah,command,data)
    return parse_response(pah,command)

def read_line(pah):
    return pah.read()

def get_menu(pah):
    lines = []
    send_command(pah,'M')
    while True:
        try:
            line = read_line(pah)
        except visa.errors.VisaIOError:
            return lines
        lines.append(line)
    return lines

NANOAMPS, MICROAMPS, MILLIAMPS = 'nA', 'uA', 'mA'
OVER_RANGE, IN_RANGE, UNDER_RANGE = '>', '=', '<'
# return (status,current) pair where:
#
#     status:
#
#         whether picoammeter is OVER_RANGE,
#         UNDER_RANGE, or IN_RANGE
#
#     current:
#
#         picoammeter current reading, in amperes
def get_current(pah):
    response = query_pa(pah,'S')
    status, rangestr, value, units = response.split(',')
    return status, float(value)*10**{
        NANOAMPS:-9,
        MICROAMPS:-6,
        MILLIAMPS:-3
    }[units]

def set_biasing(pah,biasing):
    query_pa(
        pah,
        'B',
        str(
            {
                True:1,
                False:0
            }[biasing]
        )            
    )

# TODO: set ranging, range querying
if __name__ == '__main__':
    try:
        with PicoammeterHandler() as pah:
            biasing = {
                'y':'1','n':'0'
            }[input('do you want to bias? y/n: ')]        
            print(query_pa(pah,'B',biasing))
            while True:
                try:
                    print(
                        'current: {1} amps, status: {0}'.format(
                            *(
                                fmt(d) for fmt, d in zip(
                                    (
                                        lambda status: {
                                            OVER_RANGE: 'over range',
                                            UNDER_RANGE: 'under range',
                                            IN_RANGE: 'in range'
                                        }[status],
                                        lambda num: '{:+.5e}'.format(num).rjust(15)
                                    ),
                                    get_current(pah)
                                )
                            )            
                        )
                    )
                except KeyError:
                    continue
                # response = input('enter q to quit or press enter to continue: ')
                # if response == 'q':
                #     break    
    except KeyboardInterrupt:
        print('quitting.')
        
