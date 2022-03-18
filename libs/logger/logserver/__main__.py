import sampleheater
import nozzleheater
import lakeshore
import beckhttpserver as bhs
import pfeiffer
import pyvisa
from logger import logserver as ls
import os
import math

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
            (2, 'cc P3'),
            (3, 'cc P4'),
            (4, 'cc rotary seal'),
            (5, 'cc gasline')
        )
    ), (
        pfeiffer.DG,
        (
            (0, 'fl LiHe'),
            (1, 'res LiHe')
        )
    )
)

def pfeiffer_handle():
    pressures = []
    for gauge_id, gauge_channels in pfeiffer_channels:
        while True:
            try:
                with pfeiffer.PfeifferGaugeHandler(pfeiffer.visaids[gauge_id]) as ph:
                    pressures.extend(
                        [
                            pressure for index, pressure in enumerate(pfeiffer.get_pressures(ph))
                            if index in list(list(zip(*gauge_channels))[0])
                        ]
                    )
                    break
            except pyvisa.errors.VisaIOError:
                continue
    return pressures

To = 273.15

sample_heater_channels = ['sample','sample setpoint']

def sample_heater_handle():
    with sampleheater.SampleHeaterHandler() as shh:
        return [
            shh.get_temperature(),
            shh.get_setpoint()
        ]

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

def lakeshore_handle():
    try:
        with lakeshore.LakeShoreMonitorHandler() as lsm:
            return [lsm.get_temperature()]
    except pyvisa.errors.VisaIOError as e:
        print('lakeshore error:',repr(e))
        return [math.nan]

temperature_groups = [
    (sample_heater_channels,sample_heater_handle),
    (nozzle_heater_channels,nozzle_heater_handle),
    (lakeshore_channels,lakeshore_handle)
]

def temperature_handle():
    temperatures = []
    for channels, handle in temperature_groups:
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
    # {
    #     ls.NAME:'temperatures',
    #     ls.CHANNELS:sum([channels for channels,handle in temperature_groups],[]),
    #     ls.DELTA:5.0,
    #     ls.HANDLE:temperature_handle,
    #     ls.UNITS:'kelvin'
    # }
]

# groups = [] # uncomment to disable logging (but still serve old logs)

bhs.run_beck_server(ls.PORT,os.path.dirname(__file__),ls.LoggerApp,groups,_debug=True)
