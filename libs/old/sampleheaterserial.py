# remote mode must be enabled to write to device
# (reading works in either mode)

import struct
import pyvisa
from time import time

VISAID = 'sampleheater'
ADDRESS = 1

baudrate = 57600 # per second
waittime = 4 * 10 / baudrate # seconds

crco = 0xffff
overflow = 0xa001

read_n_words = b'\x03'
write_word = b'\x06'
write_n_words = b'\x10'

product_number_add = 1001
zero_add = 0x0000

process_value_add = 2
setpoint_add = 14

d1_diode_type_add = 27

# test = b'\x01\x03\x06:\x83\x12o\x00\x00'

def crc16(data):
    crc = crco
    for b in data:
        crc ^= b
        n = 0
        while n < 8:
            carry = crc & 1
            crc >>= 1
            if carry:
                crc ^= overflow
            n += 1
    return crc

def format_word(word):
    return 

class SampleHeaterError(Exception):
    pass

class SampleHeaterHandler:
    def __init__(self,visaid=VISAID,device_address=ADDRESS):
        self.visaid = visaid
        self.device_address = device_address                

    def __enter__(self):
        self.handle = pyvisa.ResourceManager().open_resource(self.visaid)
        self.handle.baud_rate = baudrate
        self.start = time()
        return self

    def __exit__(self,*args):
        self.handle.close()

    @staticmethod
    def format_word(word):
        return struct.pack('>H',word)
    
    @staticmethod
    def format_crc(crc):
        return struct.pack('<H',crc)

    @staticmethod
    def format_byte(byte):
        return struct.pack('B',byte)

    @staticmethod
    def parse_byte(bytestr):
        return struct.unpack('B',bytestr)[0]

    @staticmethod
    def parse_word(bytestr):
        return struct.unpack('>H',bytestr)[0]

    @staticmethod
    def parse_crc(bytestr):
        return struct.unpack('<H',bytestr)[0]

    def write_message(self,function,data,cb):
        message = b''
        message += self.format_byte(self.device_address)
        message += function
        message += data
        crc = crc16(message)
        message += self.format_crc(crc)
        while time() - self.start < waittime:
            continue
        self.handle.write_raw(message)
        self.start = time()                
        head = b''
        dev_add = self.handle.read_bytes(1)
        head += dev_add        
        func_code = self.handle.read_bytes(1)        
        head += func_code
        error = self.parse_byte(func_code) // 128
        in_message = head
        if error:
            err_code = self.handle.read_bytes(1)
            in_message += err_code
            err_str = '0x{:02X}'.format(self.parse_byte(err_code))
        else:
            tail, response = cb()
            in_message += tail        
        crcread = self.parse_crc(self.handle.read_bytes(2))
        crccalc = crc16(in_message)
        assert crcread == crccalc
        if error:
            raise SampleHeaterError(err_str)
        return response

    def read_n_words_cb(self):
        message = b''        
        n_bytes_read_raw = self.handle.read_bytes(1)
        message += n_bytes_read_raw
        n_bytes_read = self.parse_byte(n_bytes_read_raw)
        data = self.handle.read_bytes(n_bytes_read)
        message += data        
        return message, data

    def read_n_words(self,start_address,n_words):
        message = b''
        message += self.format_word(start_address)
        message += self.format_word(n_words)        
        return self.write_message(
            read_n_words,
            message,
            self.read_n_words_cb
        )

    def write_n_words_cb(self):
        message = b''
        message += self.handle.read_bytes(2) # first word address
        message += self.handle.read_bytes(2) # num written words
        return message, None

    def write_n_words(self,start_address,data):
        n_bytes = len(data)
        n_words = n_bytes // 2        
        message = b''
        message += self.format_word(start_address)
        message += self.format_word(n_words)
        message += self.format_byte(n_bytes)
        message += data
        return self.write_message(
            write_n_words,message,self.write_n_words_cb
        )

    def write_word_cb(self):
        message = b''
        message += self.handle.read_bytes(2) # address
        message += self.handle.read_bytes(2) # val to be written
        return message, None

    def write_word(self,address,data):
        message = b''
        message += self.format_word(address)
        message += data
        self.write_message(write_word,message,self.write_word_cb)

    # return temperature in kelvin from binary temperature from parameter table
    @staticmethod
    def parse_temperature(raw_temperature):
        return struct.unpack('>i',raw_temperature)[0] / 100

    @staticmethod
    def format_temperature(temperature):
        return struct.pack('>i',int(100*temperature))

    def get_temperature(self):
        return self.parse_temperature(
            self.read_n_words(process_value_add,2)
        )

    def get_setpoint(self):
        return self.parse_temperature(
            self.read_n_words(setpoint_add,2)
        )

    def set_setpoint(self,temperature):
        return self.write_n_words(
            setpoint_add,
            self.format_temperature(temperature)
        )

    def get_d1_diode_type(self):
        return self.read_n_words(d1_diode_type_add,1)

    def set_d1_diode_type(self,type):
        return self.write_word(
            d1_diode_type_add,struct.pack('2B',0,type)
        )

if __name__ == '__main__':
    with SampleHeaterHandler() as shh:
        print(shh.get_temperature())
        print(shh.get_setpoint())        