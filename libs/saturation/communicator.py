import os
import struct
import ctypes
import argparse
import configparser

nobuf = 0
nfactors = 4
ndouble = ctypes.sizeof(ctypes.c_double())
nint = ctypes.sizeof(ctypes.c_int())

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'infile',
        help='name of input file'
    )
    parser.add_argument(
        'outfile',
        help='name of output file'
    )    
    parser.add_argument(
        'configfile',
        help='name of config file with experimental and computation parameters'
    )
    parser.add_argument(
        'datafolder',
        help='name of folder of sanitized data'
    )   
    parser.add_argument(
        'outfolder',
        help='name of folder to put output data into'
    )   
    parser.add_argument(
        'timestamp',
        help='root for filenames of output files'
    )    
    return parser

def get_args():
    parser = get_parser()
    return parser.parse_args()

def get_pipes(args=None):
    if args is None:
        args = get_args()
    return args.infile, args.outfile    

def get_config(args=None):
    if args is None:
        args = get_args()
    with open(args.configfile,'r') as f:
        cp = configparser.ConfigParser()
        cp.read_file(f)
    return cp

def get_data_folder(args=None):
    if args is None:
        args = get_args()
    return args.datafolder

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
            lined = {}
            datad[lineindex] = lined
            nmodes = 2
            while nmodes:
                mode = self.get_int()
                curvelength = self.get_int()
                arr = self.get_doubles(curvelength)
                lined[mode] = arr
                nmodes -= 1            
            nlines -= 1
        return datad

    def get_sse(self,factors):
        self.send_int(SSE)
        self.send_doubles(factors)
        return self.get_double()        

    def quit(self):
        self.send_int(QUIT)