import lockin
import oscilloscope as scope
import configparser
import os
from bologain import bologainclient
from logger import logclient
import datetime

LOGGER, BOLOMETER, WAVESOURCE, LOCKIN = 0, 1, 2, 3

MD_KEYS = {
    LOGGER:'logger',
    BOLOMETER:'bolometer',
    WAVESOURCE:'wave source',
    LOCKIN:'lockin'
}
_config_codes = MD_KEYS.keys()
def get_metadata(config_codes = _config_codes):    
    md = {}
    for code in config_codes:
        key = MD_KEYS[code]
        if code == LOGGER:
            value = {
                group: get_logger_params(group)
                for group in ('pfeiffer','temperatures')
            }
        elif code == BOLOMETER:
            value = get_bolometer_params()
        elif code == WAVESOURCE:
            value = get_wavesource_params()
        elif code == LOCKIN:
            value = get_lockin_params()
        md[key] = value
    return md
def get_logger_params(group):    
    date = datetime.datetime.now().date()
    units = logclient.get_units(group,date)
    channels = logclient.get_channels(group,date)
    time, data = logclient.get_most_recent(group,date)
    d = {'log entry':time.isoformat()}
    d.update(
        {
            channel:[datum,units] for channel, datum in zip(channels,data)
        }
    )
    return d

def get_bolometer_params():
    return {
        'bolo gain':(
            bologainclient.get_gain(),'x'
        )
    }

def get_wavesource_params():
    with scope.ScopeHandler() as sh:
        ws_enabled = scope.get_wavesource_enabled(sh)
        ws_shape = scope.get_wavesource_shape(sh)
        vrms = scope.get_rms_noise(sh)
        ws_load = scope.get_output_impedance(sh)
    return {
        'wavesource enabled':ws_enabled,
        'wavesource shape':ws_shape,
        'rms voltage':(vrms,'volts'),
        'wavesource impedance':ws_load
    }

def get_lockin_params(lia=None):
    try:
        if lia is None:
            lia = lockin.load_lockin()
            close = True
        else:
            close = False
        lockin_frequency = lockin.get_frequency(lia)
        lockin_phase = lockin.get_phase(lia)
        lockin_amplitude = lockin.get_mod_amp(lia)
        lockin_time_constant = lockin.get_time_constant(lia)
        lockin_sensitivity = lockin.get_sensitivity(lia)
        return {
            'mod frequency':(lockin_frequency,'hertz'),
            'phase':(lockin_phase,'degrees'),
            'mod amplitude':(lockin_amplitude,'volts'),
            'sensitivity':(lockin_sensitivity,'volts'),
            'time constant':(lockin_time_constant,'seconds')
        }
    finally:
        if close:
            lockin.close_lockin(lia)

def get_config(fname='config.ini'):
    cp = configparser.ConfigParser(allow_no_value=True)
    cp.read(fname)
    return cp

def get_config_parameter(
    config: configparser.ConfigParser,
    section,parameter,
    type=str,check=True
    ):
    if type is bool:
        value = config.getboolean(section,parameter)
    else:
        value = config[section][parameter]
    if check and value is None:
        raise Exception(
            'parameter "{}" of section "{}" must be specified'.format(
                parameter,section
            )
        )    
    return type(value)

def parse_grapher_folder(rawfolder):
    return rawfolder.split('/')

if __name__ == '__main__':
    get_logger_params('pfeiffer')    
    print('wavesource parameters:')
    print(get_wavesource_params())
    print('lockin parameters:')
    print(get_lockin_params())
