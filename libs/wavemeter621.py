from functools import reduce
import struct
import serial as ser

comport = 'COM3'
ST = 0x7E
ET = 0x7D
CT = 0x20

CMD_FREQ = 0x45
RSP_FREQ = 0x6B

def compute_checksum(msg):        
    words = []
    for n, b in enumerate(msg):
        if n % 2:
            words[-1] += 256 * b
        else:
            words.append(b)
    crc = reduce(
        lambda x, y: x ^ y, words, 0
    )
    return crc % 256, crc // 256

class Bristol621:
    def __init__(self,ser : ser.Serial):
        self.ser = ser
        self.outgoing_id = 1
        self.incoming_id = None

    def read_byte(self):
        return int.from_bytes(self.ser.read(),'little')

    def get_byte(self):
        b = self.read_byte()
        if b == ET:
            return self.read_byte() ^ CT
        else:
            return b

    def read_response(self,resp_id_o):
        assert self.read_byte() == ST
        bs = []
        def get_byte():
            bs.append(self.get_byte())
            return bs[-1]
        resp_id = get_byte()
        assert resp_id == resp_id_o
        seq_num = get_byte()
        if self.incoming_id is None:
            self.incoming_id = seq_num
        else:
            self.incoming_id += 1
            if self.incoming_id == 256:
                self.incoming_id = 1
            assert seq_num == self.incoming_id
        csl = get_byte()
        csh = get_byte()
        dl = get_byte()
        dl += get_byte() * 256        
        data = []
        # weird 2 byte padding thing I don't get
        padl = get_byte()
        padh = get_byte()
        n = 0        
        while n < dl:
            data.append(get_byte())
            n += 1        
        cspl, csph = compute_checksum(bs)
        assert cspl + 256 * csph == 0
        return data

    def send_command(self,cmd_id,data):
        bs = [cmd_id,self.outgoing_id]
        self.outgoing_id += 1
        if self.outgoing_id == 256:
            self.outgoing_id = 1
        dl = len(data)
        bs.append(dl % 256)
        bs.append(dl // 256)
        bs.extend(data)
        # padding
        bs.extend([0x05,0x01])
        bs = [
            *bs[:2], *compute_checksum(bs), *bs[2:]
        ]
        cmd = [ST]
        for b in bs:
            if b in (ST, ET):
                cmd.append(ET)
                cmd.append(b ^ CT)
            else:
                cmd.append(b)
        self.ser.write(bytes(cmd))

    def get_wavenumber(self):        
        self.send_command(CMD_FREQ,[])
        try:
            return struct.unpack(
                '<d',bytes(self.read_response(RSP_FREQ))
            )[0]
        except AssertionError:
            raise FailedResponse()
        
class FailedResponse(Exception):
    pass

class Bristol621Handler:
    def __init__(self,comport=comport):
        self.comport= comport

    def __enter__(self):
        self.ser = ser.Serial(self.comport,baudrate=921600, timeout=2)
        return Bristol621(self.ser)

    def __exit__(self,*args):
        self.ser.close()

if __name__ == '__main__':
    import time
    dt = 0.025
    with Bristol621Handler() as wmh:
        n = 1
        try:
            while True:
                print(str(n).rjust(4),':','{:.6f} cm-1'.format(wmh.get_wavenumber()).rjust(20))
                time.sleep(dt)
                n += 1
        except KeyboardInterrupt:
            print('quitting.')            