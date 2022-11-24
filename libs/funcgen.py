import pyvisa

VISAID = 'funcgen'
read_termination = write_termination = '\n'

def open_funcgen(visaid=VISAID):
    fg = pyvisa.ResourceManager().open_resource(visaid)
    fg.read_termination = read_termination
    fg.write_termination = write_termination
    return fg

def close_funcgen(handler):
    handler.close()

class FuncGenHandler:
    def __init__(self,visaid=VISAID):
        self.visaid  = visaid

    def __enter__(self):
        self.fgh = open_funcgen(self.visaid)
        return self.fgh

    def __exit__(self,*args):
        close_funcgen(self.fgh)

SOUR, OUTP = 'sour', 'outp'
def fmt_ch(prefix,channel):
    return '{}{:d}'.format(prefix,channel)

def fmt_p(channel,prefix,folders):
    return ':'.join(
        (fmt_ch(prefix,channel),*folders)
    )

def queryp(handler,channel,prefix,*folders,fmt=None):
    response = handler.query('{}?'.format(fmt_p(channel,prefix,folders)))    
    if fmt is not None:
        response = fmt(response)
    else:
        response = response.lower()        
    return response

def setp(handler,channel,value,prefix,*folders,fmt=str):
    handler.write('{} {}'.format(fmt_p(channel,prefix,folders),fmt(value)))

def get_id(handler):
    return handler.query('*idn?')

def setter(prefix,*folders,fmt=str):    
    def _setter(handler,channel,value):
        setp(handler,channel,value,prefix,*folders,fmt=fmt)
    return _setter
def getter(prefix,*folders,fmt=None):    
    def _getter(handler,channel):
        return queryp(handler,channel,prefix,*folders,fmt=fmt)
    return _getter    
def get_handles(*folders,prefix=SOUR,gfmt=None,sfmt=str):
    return getter(prefix,*folders,fmt=gfmt), setter(prefix,*folders,fmt=sfmt)

SIN, NOIS = 'sin', 'nois'
get_output_type,    set_ouput_type  = get_handles('func')
get_amplitude,      set_amplitude   = get_handles('volt',gfmt=float)
get_offset,         set_offset      = get_handles('volt','offs',gfmt=float)
VPP, VRMS = 'vpp', 'vrms'
get_units,          set_units       = get_handles('volt','unit')
get_frequency,      set_frequency   = get_handles('freq',gfmt=float)
get_bandwidth,      set_bandwidth   = get_handles('func','nois','bwid',gfmt=float)
get_output,         set_output      = get_handles(prefix=OUTP,gfmt=lambda x: bool(int(x)),sfmt=lambda x: str(int(x)))

if __name__ == '__main__':
    with FuncGenHandler() as fgh:
        print(get_id(fgh))
        print(get_output_type(fgh,1))
        print(get_bandwidth(fgh,1))
        print(get_output(fgh,1))
        set_output(fgh,1,False)
        print(get_output(fgh,1))