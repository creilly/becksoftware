# remote mode must be enabled to write to device
# (reading works in either mode)

from pickle import PROTO
import struct
import pyvisa
from time import time

VISAID = 'sampleheaterethernet'
ADDRESS = 1
PROTOCOL = 0

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

class SampleHeaterError(Exception):
    pass

class SampleHeaterHandler:
    def __init__(self,visaid=VISAID,device_address=ADDRESS):
        self.visaid = visaid
        self.message_index = 0              

    def __enter__(self):
        self.handle = pyvisa.ResourceManager().open_resource(self.visaid)
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

    def write_message(self,function,data):
        message = b''
        message += self.format_word(self.message_index) # transaction id
        message += self.format_word(PROTOCOL) # protocol id
        # data length:        
        # * 1 byte for device address
        # * 1 byte for function code
        # * len(data) bytes for message data
        message += self.format_word(1 + 1 + len(data)) 
        message += self.format_byte(ADDRESS) # device address        
        message += function # function code
        message += data # message data
        # print('out message data',data)
        # print('out message',message)
        self.handle.write_raw(message)
        head = b''
        tid = self.parse_word(self.handle.read_bytes(2))
        assert tid == self.message_index
        # print('message index',self.message_index,'tid',tid)
        pid = self.parse_word(self.handle.read_bytes(2))
        # print('protocol',PROTOCOL,'pid',pid)
        datalen = self.parse_word(self.handle.read_bytes(2))
        # print('datalen',datalen)
        devadd = self.parse_byte(self.handle.read_bytes(1))
        # print('address',ADDRESS,'devadd',devadd)
        func_code = self.handle.read_bytes(1)
        # print('function',function,'func_code',func_code)
        # message data length is equal to:
        # * + data length 
        # * - 1 byte for device address
        # * - 1 byte for func code
        messagedatalen = datalen-1-1
        self.message_index = (self.message_index + 1) % 2**16
        error = self.parse_byte(func_code) // 128
        if error:
            err_code = self.handle.read_bytes(1)
            err_str = '0x{:02X}'.format(self.parse_byte(err_code))
            raise SampleHeaterError(err_str)
        messagedata = self.handle.read_bytes(messagedatalen)
        return messagedata

    def read_n_words(self,start_address,n_words):
        message = b''
        message += self.format_word(start_address)
        message += self.format_word(n_words)        
        data = self.write_message(
            read_n_words,
            message            
        )
        # print('message data to read n words',data)
        n_bytes_read_raw = data[0:1]
        n_bytes_read = self.parse_byte(n_bytes_read_raw)
        # print('message data len',len(data),'n bytes read',n_bytes_read)
        return data[1:][:n_bytes_read]

    def write_n_words(self,start_address,data):
        n_bytes = len(data)
        n_words = n_bytes // 2        
        message = b''
        message += self.format_word(start_address)
        message += self.format_word(n_words)
        message += self.format_byte(n_bytes)
        message += data
        indata = self.write_message(
            write_n_words,message
        )
        # print('expected mess data len',4,'actual mess data len',len(data))
        first_word_add = self.parse_word(data[:2])
        # print('start add',start_address,'first word add',first_word_add)
        num_words_written = self.parse_word(data[2:])
        # print('expect num words written',len(data)//2,'num words written',num_words_written)

    def write_word(self,address,data):
        message = b''
        message += self.format_word(address)
        message += data
        indata = self.write_message(write_word,message)
        add_written = self.parse_word(data[:2])
        # print('add to write',address,'add written',add_written)
        val_written = data[2:]
        # print('data to write',data,'data written',val_written)
        
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
        print('\t','temperature',shh.get_temperature())
        print('\t','setpoint',shh.get_setpoint())
        print('\t','diode type',shh.get_d1_diode_type())
        shh.set_d1_diode_type(1)
        print('\t set diode type to 1')
        print('\t','diode type',shh.get_d1_diode_type())
        shh.set_d1_diode_type(0)
        print('\t set diode type to 0')
        print('\t','diode type',shh.get_d1_diode_type())