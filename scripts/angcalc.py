import math
import argparse

surfthetao = 0 # degs
micthetao = 60 # update 2023-01-09 # 35 # degs

dmic_dsurf = -21.0 # degs mic per deg surf

POS, NEG = 0, 1

def get_digits(n):
    return int(math.log10(n)) + 1

def get_mictheta(surftheta):
    return micthetao + dmic_dsurf * (surftheta-surfthetao)

def get_sense(mictheta1,mictheta2):
    return POS if mictheta2 > mictheta1 else NEG

def parse_mictheta(mictheta):
    turns = 0    
    while True:
        if mictheta > 360:
            turns += 1
            mictheta -= 360
            continue
        if mictheta < 0:
            mictheta += 360
            turns -= 1
            continue
        return turns, mictheta

def get_turns(mictheta):
    return parse_mictheta(mictheta)[0]

def get_remainder(mictheta):
    return int(round(parse_mictheta(mictheta)[1]))

def get_marker(sense,remainder):
    return {
        POS:remainder,
        NEG:360-remainder
     }[sense]

dird = {
    POS:'clockwise',
    NEG:'counterclockwise'
}

signd = {
    POS:+1,NEG:-1
}

def get_steps(mictheta1, mictheta2):
    steps = []    
    turns1, remainder1 = (
        f(mictheta1) for f in (get_turns,get_remainder)
    )    
    turns2, remainder2 = (
        f(mictheta2) for f in (get_turns,get_remainder)
    )    
    sense = get_sense(mictheta1,mictheta2)    
    steps.append(
        'micrometer should currently read {:d} degrees'.format(remainder1)
    )
    deltaturns = turns2 - turns1
    if not deltaturns:
        steps.append(
            'move micrometer {} to the {:d} degrees marker without crossing zero'.format(
                dird[sense],
                remainder2
            )
        )
        return steps        
    steps.append(
        'advance micrometer {} to the 0 degrees marker'.format(dird[sense])
    )
    fullturns = abs(deltaturns)-1
    if fullturns:
        steps.append(
            'continue advancing micrometer {} by {:d} full {} to next 0 degrees marker'.format(dird[sense],fullturns,'turns' if fullturns > 1 else 'turn')
        )
    steps.append(
        'continue advancing micrometer {} to the {:d} degrees marker'.format(dird[sense],remainder2)
    )
    steps.append('all done!')
    return steps

def format_steps(steps):
    fmt = 'step # {{: {:d}d}} : {{}}'.format(get_digits(len(steps)-1))
    return '\n'.join(
        fmt.format(index,step) for index, step in enumerate(steps)
    )

surftheta1 = float(input('enter starting surface angle\t:\t'))
surftheta2 = float(input('enter ending surface angle\t:\t'))

mictheta1 = get_mictheta(surftheta1)
mictheta2 = get_mictheta(surftheta2)

print(format_steps(get_steps(mictheta1,mictheta2)))