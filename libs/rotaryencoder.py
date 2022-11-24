import serial

comport = 'COM10'

GET_COMMAND = b'g'
READ_TERM = b' '

def open_rotary_encoder():
    return serial.Serial(comport,dsrdtr=True)

class RotaryEncoderHandler():
    def __enter__(self):
        self.handle = open_rotary_encoder()
        return self.handle

    def __exit__(self,*args):
        close_rotary_encoder(self.handle)

def close_rotary_encoder(handle):
    handle.close()

def get_position(handle):
    handle.write(GET_COMMAND)
    response = b''
    while True:
        b = handle.read(1)
        if b == READ_TERM:
            return int(response.decode('utf8'))
        response += b

if __name__ == '__main__':
    with RotaryEncoderHandler() as reh:
        print('position:',get_position(reh))