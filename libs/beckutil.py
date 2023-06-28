import os
import ctypes as c

DLL_EV = 'BECKDLL'
dll_path = os.environ[DLL_EV]
os.add_dll_directory(dll_path)

def load_dll(dllname):
    return c.windll.LoadLibrary(dllname)

colorcodes = {
    'purple':   '\x1b[95m',
    'blue'  :   '\x1b[94m',
    'cyan'  :   '\x1b[96m',
    'green' :   '\x1b[92m',
    'yellow':   '\x1b[93m',
    'red'   :   '\x1b[91m',
    'dred'  :   '\x1b[31m',
    'grey'  :   '\x1b[90m'
}
colors = ('blue', 'green', 'purple', 'red', 'cyan', 'yellow')
endcolor = '\x1b[0m'
def print_color(color,*args):
    print(''.join((colorcodes[color],*args,endcolor)))