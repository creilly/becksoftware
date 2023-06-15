import os
import struct
import ctypes
import argparse
import configparser

nobuf = 0
nfactors = 4
ndouble = ctypes.sizeof(ctypes.c_double())
nint = ctypes.sizeof(ctypes.c_int())

class Parser:
    IN, OUT = 0, 1
    def __init__(self,parser=None):
        if parser is None:
            parser = argparse.ArgumentParser()
        parser.add_argument(
            '-a','--infile',
            help='name of input file'
        )
        parser.add_argument(
            '-b','--outfile',
            help='name of output file'
        )    
        parser.add_argument(
            '-c','--configfile',
            help='name of config file with experimental and computation parameters'
        )        
        parser.add_argument(
            '-t','--timestamp',
            help='root for filenames of output files'
        )
        self.parser = parser

    def get_arg(self,key):
        return getattr(self.parser.parse_args(),key)

    def get_config(self):        
        return get_config(self.get_arg('configfile'))        

    def get_infile(self):
        return self.get_file(self.IN)
    def get_outfile(self):
        return self.get_file(self.OUT)
    def get_file(self,dir):
        return self.get_arg({self.IN:'infile',self.OUT:'outfile'}[dir])

    def get_timestamp(self):
        return self.get_arg('timestamp')

def get_config(config_fname):
    with open(config_fname,'r') as f:
        cp = configparser.ConfigParser()
        cp.read_file(f)
    return Config(cp)

class Config:
    COMP = 'computational'
    EXP = 'experimental'
    def __init__(self,cp):
        self.cp = cp

    def get_value(self,section,key,type=None):
        rawvalue = self.cp.get(section,key)
        return rawvalue if type is None else type(rawvalue)

    def get_comp(self,key,type=None):
        return self.get_value(self.COMP,key,type)

    def get_exp(self,key,type=None):
        return self.get_value(self.EXP,key,type)

    def get_datafolder(self):
        return self.get_comp('datafolder')

    def get_factors(self):
        return [float(f) for f in self.get_comp('factors').split(',')]

    def get_outputfolder(self):
        return self.get_comp('outputfolder')

    def get_N(self):
        return self.get_comp('N',int)

    def get_step_size(self):
        return self.get_comp('step size',float)

    def get_max_iters(self):
        return self.get_comp('M',int)

    def get_velocity(self):
        return self.get_exp('velocity',float)

    def get_diameter(self):
        return self.get_exp('diameter',float)

    def get_vrms(self):
        return self.get_exp('vrms',float)

    def get_mask(self):
        return [{'0':False,'1':True}[b.strip()] for b in self.get_comp('mask').strip().split(',')]

    def get_weights(self):
        return [float(f) for f in self.get_comp('weights').split(',')]

class Communicator:
    def __init__(self,inpipe_fname,outpipe_fname):        
        fd = os.open(
            inpipe_fname,
            os.O_RDONLY | os.O_NONBLOCK
        )        
        self.inpipe = open(fd,'rb',nobuf)        
        self.outpipe = open(outpipe_fname,'wb',nobuf)

    def read(self,bytestoread,cb=None):
        response = b''
        while bytestoread:
            chunk = self.inpipe.read(bytestoread)
            if chunk is not None:
                bytestoread -= len(chunk)
                response += chunk
            if cb is not None:
                cb()
        return response    

    def get_ints(self,n):
        return self._get_data(n,nint,'i')

    def get_int(self):
        return self.get_ints(1)[0]

    def get_doubles(self,n):
        return self._get_data(n,ndouble,'d')

    def get_double(self):
        return self.get_doubles(1)[0]

    def _get_data(self,n,s,f):
        return struct.unpack('{:d}{}'.format(n,f),self.read(n*s))

    def send_ints(self,ints):
        self.send_data(ints,'i')

    def send_int(self,integer):
        self.send_ints([integer])

    def send_doubles(self,doubles):
        self.send_data(doubles,'d')

    def send_double(self,double):
        self.send_doubles([double])

    def send_data(self,data,f):
        self.outpipe.write(
            struct.pack(
                '{:d}{}'.format(len(data),f),*data
            )
        )        

class Server(Communicator):        

    def get_factors(self):
        return self.get_doubles(nfactors)

    def send_sse(self,sse):
        self.send_double(sse)        

SSE, DATA, QUIT = 0, 1, 2
class Client(Communicator):

    def get_data(self,factors):
        datad = {}
        self.send_int(DATA)
        self.send_doubles(factors)
        nlines = self.get_int()                
        while nlines:
            lineindex = self.get_int()            
            curvelength = self.get_int()
            datad[lineindex] = self.get_doubles(curvelength)
            nlines -= 1
        return datad

    def get_sse(self,factors):
        self.send_int(SSE)
        self.send_doubles(factors)
        return self.get_double()        

    def quit(self):
        self.send_int(QUIT)