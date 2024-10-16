import pyvisa

class VisaHandler():
    def __init__(self,visaid,readterm,writeterm):
        self.visaid = visaid
        self.readterm = readterm
        self.writeterm = writeterm

    def __enter__(self):
        self.handle = open_device(self.visaid)
        self.handle.read_termination = self.readterm
        self.handle.write_termination = self.writeterm
        self.configure()
        return self.handle
    
    def configure(self):
        pass

    def __exit__(self,*args):
        close_device(self.handle)

class VisaSerialHandler(VisaHandler):
    def __init__(
            self,
            visaid,
            readterm,
            writeterm,
            baudrate,
            databits,
            stopbits,
            parity
        ):
            super().__init__(visaid,readterm,writeterm)
            self.baudrate = baudrate
            self.databits = databits
            self.stopbits = stopbits
            self.parity = parity

    def configure(self):
        h = self.handle
        h.baud_rate = self.baudrate
        h.data_bits = self.databits
        h.stop_bits = self.stopbits
        h.parity = self.parity

def open_device(visaid):
     return pyvisa.ResourceManager().open_resource(visaid)

def close_device(handle):
     return handle.close()