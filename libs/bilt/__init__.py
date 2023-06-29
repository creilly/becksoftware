import config

gcp = config.get_config_parameter

dwdf = 1 / 30e3 # cm-1 per MHz

def get_wavemeter_offset(cfg):
    w_ref_ref = gcp(cfg,'reference line','reference wavenumber',float) # cm-1
    w_ref_meas = gcp(cfg,'reference line','measured wavenumber',float)    
    dw = w_ref_meas - w_ref_ref
    return dw

RS, LI, PI, AWM, MA, IH, RST = 0, 1, 2, 3, 4, 5, 6