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

zero_add = 0x0000

status_add = 0
process_value_add = 2
setpoint_add = 14

work_mode_add = 21
heating_mode_add = 22
d1_diode_type_add = 27
process_value_unit_add = 30
ccr_res_op_add, ccr_res_op_unit_add, \
    ccr_res_sb_add, ccr_res_sb_unit_add = 31, 32, 33, 34
ccr_eb_op_add, ccr_eb_op_unit_add, \
    ccr_eb_sb_add, ccr_eb_sb_unit_add = 35, 36, 37, 38
vr_op_add, vr_op_unit_add, \
    vr_sb_add, vr_sb_unit_add = 39, 40, 41, 42
cc_sp_add, cc_add, cv_add = 58, 59, 60
ev_sp_add, ev_add, ec_add = 61, 62, 63
goto_op_add, goto_sb_add = 70, 71
release_add = 1000
product_number_add = 1001
serial_number_add = 1009
rcs_add = 1151
di_cn_add, di_fc_add, di_ch_add = 1200, 1201, 1202
relay_mode_add_o = 1300
di_sense_base_add = 1202

class SampleHeaterError(Exception):
    pass

KELVIN, CELSIUS, FAHRENHEIT, VOLT = 0, 1, 2, 3
RES, EB = 0, 1
OPERATE, STANDBY = 1, 0
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
    def format_word(word,signed=False):
        return struct.pack('>{}'.format({False:'H',True:'h'}[signed]),word)
    
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
    def parse_word(bytestr,signed=False):
        return struct.unpack('>{}'.format({False:'H',True:'h'}[signed]),bytestr)[0]

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
    
    def get_word(self,address,signed=False):
        return self.parse_word(
            self.read_n_words(address,1), 
            signed = signed
        )

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
        return(indata)

    def write_word(self,address,data):
        message = b''
        message += self.format_word(address)
        message += data
        indata = self.write_message(write_word,message)     
        return(indata)
    
    def set_word(self,address,word,signed=False):
        return self.write_word(
            address, self.format_word(word,signed)
        )
        
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
    
    def release_control(self):
        return self.write_word(release_add,RELEASE)
    
    def get_remote_control_status(self):
        return self.get_word(rcs_add)
    
    def get_work_mode(self):
        return int(self.read_n_words(work_mode_add,1)[0])
    
    def get_serial_number(self):
        return self.read_n_words(serial_number_add,7)[:-1]
    
    def get_process_value_unit(self):
        return int(self.read_n_words(process_value_unit_add,1)[0])
    
    # mode: RES or EB
    # state: OPERATE or STANDBY
    CCR_MULT = 100
    def get_current_ramp(self,mode,state):
        return self.get_word(
            {
                RES:{
                    OPERATE:ccr_res_op_add, STANDBY:ccr_res_sb_add
                },
                EB:{
                    OPERATE:ccr_eb_op_add, STANDBY:ccr_eb_sb_add
                }
            }[mode][state]
        ) / self.CCR_MULT
    
    AMPS_PER_SEC, AMPS_PER_MIN, AMPS_PER_HOUR = 0, 1, 2
    def get_current_ramp_units(self,mode,state):
        return self.get_word(            
            {
                RES:{
                    OPERATE:ccr_res_op_unit_add, STANDBY:ccr_res_sb_unit_add
                },
                EB:{
                    OPERATE:ccr_eb_op_unit_add, STANDBY:ccr_eb_sb_unit_add
                }
            }[mode][state]
        )
    
    VR_MULT = 10
    def get_voltage_ramp(self,state):
        return self.get_word(
            {OPERATE:vr_op_add,STANDBY:vr_sb_add}[state]
        ) / self.VR_MULT
    
    VOLTS_PER_SEC, VOLTS_PER_MIN, VOLTS_PER_HOUR = 0, 1, 2
    def get_voltage_ramp_units(self,state):
        return self.get_word(
            {OPERATE:vr_op_unit_add,STANDBY:vr_sb_unit_add}[state]
        )
    
    CC_MULT = 100 
    def get_cc_setpoint(self):
        return self.get_word(cc_sp_add) / self.CC_MULT
    
    # setpoint in amps
    def set_cc_setpoint(self,setpoint):
        return self.set_word(
            cc_sp_add, int(round(setpoint * self.CC_MULT))
        )
    
    # cathode current (i.e. filament current)
    # units : amps
    def get_cc(self):
        return self.get_word(cc_add,signed=True) / self.CC_MULT
    
    CV_MULT = 10
    # cathode voltage
    # units : volts
    def get_cv(self):
        return self.get_word(cv_add,signed=True) / self.CV_MULT
    
    EV_MULT = 10
    def get_ev_setpoint(self):
        return self.get_word(ev_sp_add) / self.EV_MULT
    
    def set_ev_setpoint(self,ev):
        return self.set_word(ev_sp_add, ev * self.EV_MULT)
    
    def get_ev(self):
        return self.get_word(ev_add) / self.EV_MULT
    
    EC_MULT = 1000
    def get_ec(self):
        return self.get_word(ec_add) / self.EC_MULT
    
    def get_di_cn(self):
        return self.get_word(di_cn_add)
    
    def get_di_fc(self):
        return self.get_word(di_fc_add)
    
    INTERLOCK, OPERATE_ON, OPERATE_OFF = 1, 2, 3
    PRESSURE_EMISS_ON, PRESSURE_EMISS_OFF = 4, 5
    OPEN_SHUTTER, CLOSE_SHUTTER = 6, 7
    ZERO_THICKNESS, ZERO_SHUTTER_TIME = 8, 9
    REMOTE_CONTROL = 10
    def set_di_fc(self,fc):
        return self.set_word(di_fc_add,fc)
    
    def get_di_ch(self):
        return self.get_word(di_ch_add)
    
    def set_di_ch(self,di_channel):
        return self.set_word(di_ch_add,di_channel)
    
    def get_di_sense(self,di_channel):
        return self.get_word(di_sense_base_add + di_channel)
    
    def set_di_sense(self,di_channel,sense):
        return self.set_word(di_sense_base_add + di_channel, sense)
    
    def get_heating_mode(self):
        return self.get_word(heating_mode_add)
    
    def set_heating_mode(self,heating_mode):
        return self.set_word(heating_mode_add,heating_mode)
    
    def get_operation_mode(self):
        return self.get_word(status_add) % 2
    
    def _go_to_mode(self,mode_add):
        return self.write_word(mode_add,GOTO)
    
    def go_to_operate(self):
        return self._go_to_mode(goto_op_add)
    
    def go_to_standby(self):
        return self._go_to_mode(goto_sb_add)
    
    @staticmethod
    def _get_relay_add(relay):
        return relay_mode_add_o + 2 * (relay - 1)
    ST_OFF, ST_ON = 1, 2
    def get_relay_mode(self,relay):
        return self.get_word(self._get_relay_add(relay))
    
    def set_relay_mode(self,relay,mode):
        return self.set_word(self._get_relay_add(relay),mode)

# note: this is in contradiction 
# with the Heat3 manual, which indicates 
# that a 0 byte must be sent to release 
# control. my tests show that 0 doesn't work, 
# but 1 does.
RELEASE = b'\x00\x01'
GOTO = b'\x00\x01'
if __name__ == '__main__':
    from time import sleep
    with SampleHeaterHandler() as sh:
        print(sh.get_relay_mode(5))