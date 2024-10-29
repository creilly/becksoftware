# from topo import ttco2 as co2
from topo import ttch4 as ch4
from topo import ttnh3 as nh3

MOTOR, ETALON = 0, 1

def get_parameter(param,w):
    if w > 3270 and w < 3525:
        mod = nh3
    elif w > 2780 and w < 3250:
        mod = ch4
    # elif w > 3350 and w < 3950:
    #     mod = co2    
    else:
        Exception('wnum {:.4} cm-1 not calibrated!'.format(w))
    return getattr(
        mod,'get_{}'.format(
            {
                MOTOR:'motor',
                ETALON:'etalon'
            }[param]
        )
    )(w)

def get_etalon(w):
    return get_parameter(ETALON,w)

def get_motor(w):
    return get_parameter(MOTOR,w)
