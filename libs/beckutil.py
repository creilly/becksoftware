import os
import ctypes as c

DLL_EV = 'BECKDLL'
dll_path = os.environ[DLL_EV]
os.add_dll_directory(dll_path)

def load_dll(dllname):
    return c.windll.LoadLibrary(dllname)
