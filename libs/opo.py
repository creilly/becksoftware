import json, os, datetime, topo, wavemeter

PATHENV = 'OPOPATH'
try:
    root = os.environ[PATHENV]    
except KeyError:
    print('env var "{}" not defined!'.format(PATHENV))
    exit(1)

fieldwidth = 4

extension = 'line'

def get_creation_time(htline,entry_code):
    return datetime.datetime.fromtimestamp(
        os.path.getctime(fmt_entry_path(htline,entry_code))
    )

def open_entry(htline,entry_code):
    with open(fmt_entry_path(htline,entry_code),'r') as f:
        return json.load(f)
    
def parse_entry(entry):
    return int(entry.split('.')[0])

def fmt_entry(entry_code):
    return '{{:0{:d}d}}.{}'.format(fieldwidth,extension).format(entry_code)

def fmt_entry_path(htline,entry_code):
    return fmt_path(*htline,fmt_entry(entry_code))

def validate(fname):
    try:
        head, tail = fname.split('.')
        assert tail == extension        
        assert len(head) == fieldwidth
        assert all(map(str.isdigit,head))   
        return True     
    except (ValueError, AssertionError):
        return False

def fmt_path(*levels):
    return os.path.join(root,*levels)

def get_entries(htline):
    try:
        return [
            *map(
                parse_entry,sorted(filter(validate,os.listdir(fmt_path(*htline))))
            )
        ]
    except FileNotFoundError:
        return []
    
def get_latest(htline):
    try:
        return get_entries(htline)[-1]
    except IndexError:
        return None
    
def open_latest(htline):
    entry_code = get_latest(htline)
    if entry_code is None:
        return None
    return open_entry(htline,entry_code)

LINE = 'line'
ETALON = 'etalon'
MOTOR = 'motor'
PIEZO = 'piezo'
TEMPERATURE = 'temperature'
WAVENUMBER = 'wavenumber'
def add_entry(htline,etalon,motor,piezo,temperature,wavenumber=None):
    path = fmt_path(*htline)
    if not os.path.exists(path):
        os.makedirs(path)
    latest = get_latest(htline)
    if latest is None:
        entry_code = 0
    else:
        entry_code = latest + 1
    with open(fmt_entry_path(htline,entry_code),'w') as f:
        json.dump(
            {
                key:value for key, value in (
                    (ETALON,etalon),
                    (MOTOR,motor),
                    (PIEZO,piezo),
                    (TEMPERATURE,temperature),
                    (WAVENUMBER,wavenumber)
                )
            },f,
            indent=2,sort_keys=True
        )
    return entry_code

def get_parameters():
    ic = topo.InstructionClient()
    etalon = ic.get_etalon_pos()
    motor = ic.get_motor_set_pos()
    piezo = ic.get_piezo()
    temperature = ic.get_diode_set_temperature()    
    with wavemeter.WavemeterHandler() as wmh:
        wavenumber = wavemeter.get_wavenumber(wmh)
    return etalon, motor, piezo, temperature, wavenumber


if __name__ == '__main__':
    htline = r' 6	1	    0 0 0 0 1A1	    0 1 0 1 1F2	    0A1  1     	    1A2  2     '.split('\t')
    ct = get_creation_time(
        htline,get_latest(htline)
    )
    print('ct',ct)