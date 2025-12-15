import daqmx, sampleheater, nozzleheater, lakeshore, pfeiffer, pyvisa, math, time
from logger import logserver as ls

pfeiffer_channels = (
    (
        pfeiffer.FL,
        (
            (0, 'fl P1, P2'),
            (1, 'fl P3, P4'),
            (2, 'fl rot seal'),
            (3, 'gas man pirani'),
            (4, 'gas man piezo')
        )
    ), (
        pfeiffer.HV,
        (
            (0, 'cc P1'),
            (1, 'cc P2'),
            (2, 'cc P3'),
            (3, 'cc P4'),
            (4, 'cc rotary seal'),
            (5, 'cc gasline')
        )
    ), (
        pfeiffer.DG,
        (
            (0, 'fl LiHe'),
            # (1, 'res LiHe')
        )
    )
)

def pfeiffer_handle():
    pressures = []
    for gauge_id, gauge_channels in pfeiffer_channels:
        while True:
            try:
                with pfeiffer.PfeifferGaugeHandler(pfeiffer.visaids[gauge_id]) as ph:
                    gauge_pressures = {
                        index:pressure for index, pressure in enumerate(pfeiffer.get_pressures(ph))
                    }
                    gauge_indexes = set(list(zip(*gauge_channels))[0])
                    if not gauge_indexes.issubset(gauge_pressures.keys()):
                        print('error: response does not contain all gauges')
                        print('requested indices:')
                        print(gauge_channels)
                        print('received indices:')
                        print(gauge_pressures.keys())
                        continue
                    pressures.extend(
                        [
                            gauge_pressures[index] 
                            for index in gauge_indexes
                        ]
                    )
                    break
            except pyvisa.errors.VisaIOError:
                print('gauge id',gauge_id,'channels',gauge_channels)
                print('pfeiffer io error')
                pressures.extend([math.nan] * len(gauge_channels))
                break
            except pfeiffer.PfeifferError as pe:
                print('pfeiffer format error: {}'.format(repr(pe)))
                pressures.extend([math.nan] * len(gauge_channels))
                break
    return pressures

To = 273.15

sample_heater_channels = ['sample','sample setpoint']

def sample_heater_handle():
    temps = []
    for foo in ('get_temperature','get_setpoint'):
        try:
            with sampleheater.SampleHeaterHandler() as shh:            
                temp = getattr(shh,foo)()
        except (ConnectionRefusedError, pyvisa.errors.VisaIOError) as e:
            print('error connecting to sample heater:',type(e))
            temp = math.nan
        temps.append(temp)
    return temps
        
nozzle_heater_channels = ['nozzle','nozzle holder','tantalum']
nozzle_heater_indices = [0,1,2]

def nozzle_heater_handle():
    try:
        with nozzleheater.NozzleHeaterHandler() as nhh:
            output = nozzleheater.get_output(nhh)
            return [output[i] + To for i in nozzle_heater_indices]
    except pyvisa.errors.VisaIOError as e:
        print('nozzle heater visa io error:',repr(e))
        return [math.nan] * len(nozzle_heater_indices)
    
lakeshore_channels = ['bolometer diode']
timer = [None]
dt_ls = 300.0 # seconds
def lakeshore_handle():
    try:
        to = timer[0]
        if to is None or time.time() - to > dt_ls:
            with lakeshore.LakeShoreMonitorHandler() as lsm:
                return [lsm.get_temperature()]
        else:
            return [math.nan]
    except pyvisa.errors.VisaIOError as e:
        print('lakeshore error:',repr(e))        
        timer[0] = time.time()
        return [math.nan]

daqmx_channels = ['snout tc'] # ['snout tc','bakeout tc']

def daqmx_handle():
    temps = []
    for logger_channel in daqmx_channels:
        try:
            with daqmx.TaskHandler(
                [
                    {
                        'snout tc':'snout thermocouple',
                        'bakeout tc':'bakeout thermocouple'
                    }[logger_channel]
                ]
            ) as ai:
                temp = daqmx.read_analog_f64_scalar(ai) + (
                    273.15 if logger_channel == 'bakeout tc' else 0.0
                )
        except daqmx.DAQmxError:
            temp = math.nan
        temps.append(temp)
    return temps

temperature_groups = [
    (sample_heater_channels,sample_heater_handle),
    (nozzle_heater_channels,nozzle_heater_handle),
    (lakeshore_channels,lakeshore_handle),
    (daqmx_channels,daqmx_handle)
]

def temperature_handle():
    temperatures = []
    for channel, handle in temperature_groups:
        temperatures.extend(handle())
    return temperatures

groups = [
    {
        ls.NAME:'pfeiffer',
        ls.CHANNELS:sum(
            [list(list(zip(*gauge_channels))[1]) for gauge_index, gauge_channels in pfeiffer_channels],[]
        ),
        ls.DELTA:5.0,
        ls.HANDLE:pfeiffer_handle,
        ls.UNITS:'mbar'
    },
    {
        ls.NAME:'temperatures',
        ls.CHANNELS:sum([channels for channels,handle in temperature_groups],[]),
        ls.DELTA:5.0,
        ls.HANDLE:temperature_handle,
        ls.UNITS:'kelvin'
    }
]