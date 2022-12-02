import config
from bologain import bologainclient
from bilt import LI, gcp, get_wavemeter_offset
from grapher import graphclient as gc

LS, FS, FC, AS = 0, 1, 2, 3

ls_f = ['line searches']
fs_f = ['frequency scans']
fc_f = ['fluence curves']
as_f = ['angular scans']

folderd = {
    LS:ls_f,
    FS:fs_f,
    FC:fc_f,
    AS:as_f
}

linecols = [
    'trans cav setpoint (MHz)',
    'lockin x (v)',
    'lockin y (v)',
    'ir photodiode (v)',
    'measured wavenumber (cm-1)'
]

ditherbasecols = [    
    'x on (v)',
    'y on (v)',
    'ir on (v)',
    'w on (cm-1)',
    'x off (v)',
    'y off (v)',
    'ir off (v)',                    
    'w off (cm-1)',
    'delta x (mm)',
    'delta y (mm)'
]

ls_c = linecols
fs_c = linecols
fc_c = ['hwp angle (degs)'] + ditherbasecols
as_c = ['lid angle (degs)'] + ditherbasecols + ['time stamp (seconds since epoch)'] + ['encoder position (steps)']

colsd = {
    LS:ls_c,
    FS:fs_c,
    FC:fc_c,
    AS:as_c
}

# contains: lower global quanta, lower local quanta, upper local quanta
def namer(htline):
    return ','.join(
        [
            ' '.join(
                htline[index].strip().split()
            ) for index in (2,4,5)
        ]
    )

def create_dataset(mode,namer,line,cfg,trial,sens_md,handlerd,do):
    path = gc.add_dataset(
        gc.get_day_folder() + folderd[mode],
        namer(line[0]),
        colsd[mode],
        metadata = create_metadata(cfg,line,trial,sens_md,handlerd,do)
    )
    return path

def create_metadata(cfg,line,trial,sens_md,handlerd,do={}):
    exp_desc = gcp(cfg,'experiment','description')
    inc_angle = gcp(cfg,'scattering','incident angle',float) # degrees
    dir_angle = gcp(cfg,'scattering','direct angle',float)
    spc_angle = gcp(cfg,'scattering','specular angle',float)
    mir_angle = gcp(cfg,'scattering','mirror angle',float)
    lid_angle = gcp(cfg,'scattering','lid angle',float)
    mixture = gcp(cfg,'scattering','gas mixture')
    w_ref_ref = gcp(cfg,'reference line','reference wavenumber',float) # cm-1
    w_ref_meas = gcp(cfg,'reference line','measured wavenumber',float)
    w_ref_line = gcp(cfg,'reference line','line')
    dw = get_wavemeter_offset(cfg)
    metadata = {
        'experiment':exp_desc,
        'sensitivity':sens_md,
        'hitran line':line[0],
        'scattering':{
            'incident angle':(inc_angle,'degrees'),
            'specular angle':(spc_angle,'degrees'),
            'direct angle':(dir_angle,'degrees'),
            'lid angle':(lid_angle,'degrees'),
            'mirror angle':(mir_angle,'degrees'),
            'mixture':(mixture,'percent')
        },
        'wavemeter':{
            'reference line':w_ref_line,
            'reference value':(w_ref_ref,'cm-1'),
            'measured value':(w_ref_meas,'cm-1'),
            'wavemeter offset':(dw,'cm-1')
        },
        'wavesource':config.get_wavesource_params(),
        'lockin':config.get_lockin_params(handlerd[LI]),
        'bolometer gain':(bologainclient.get_gain(),'X'),
        'capacitor':(0.1,'microfarad'),
        'logger':{
            group:config.get_logger_params(group)
            for group in ('pfeiffer','temperatures')
        },
        'trial':trial
    }
    metadata.update(do)
    return metadata