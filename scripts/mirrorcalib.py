import mirrormotion as mm
import pi
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('-r','--radius',default=mm.ro,type=float)

Ro = ap.parse_args().radius

Xo = 25.0
Yo = 40.0

OFF, ON, HOME, SET_POS, SET_ANG, VEL, QUIT = 1, 2, 3, 4, 5, 6, 7

commands = (OFF,ON,HOME,SET_POS,SET_ANG,VEL,QUIT)

named = {
    OFF:'set motors off',
    ON:'set motors on',
    HOME:'home motors',
    SET_POS:'set motor positions',
    SET_ANG:'set mirror angle',
    VEL:'set motor velocity',
    QUIT:'quit'
}

axes = (pi.X,pi.Y)

axesnamed = {pi.X:'x', pi.Y:'y'}

def callback(pih,coordsp,coordso):
    def _callback():
        coords = {
            axis:pi.get_position(pih,axis)
            for axis in axes
        }
        progresses = {
            axis:abs(
                (coords[axis]-coordso[axis])/(coordsp[axis]-coordso[axis])
            ) if coordsp[axis]!=coordso[axis] else 1.0
            for axis in axes
        }
        print(
            'moving motors. progress:',
            '\t,\t'.join(
                [
                    '{} : {}'.format(
                        axesnamed[axis],
                        '{: 3d} %'.format(
                            int(round(100*progresses[axis]))
                        )
                    ) for axis in axes
                ]
            )
        )
    return _callback
        
while True:
    with pi.PIHandler() as pih:
        print(
            'states:', ' , '.join(
                [
                    '{} : {}'.format(
                        axesnamed[axis],
                        {
                            True:' on',
                            False:'off'
                        }[pi.get_motor_state(pih,axis)]
                    ) for axis in axes
                ]
            ),
            '|',
            'positions:', ' , '.join(
                [
                    '{} : {} mm'.format(
                        axesnamed[axis],
                        '{:.2f}'.format(pi.get_position(pih,axis)).rjust(6)
                    ) for axis in axes
                ]
            )
        )
    for command in commands:
        print('{:d} : {}'.format(command,named[command]))
    option = input('select an option: ')
    if not option.isdigit():
        print('option must be a number')
        continue
    option = int(option)
    if option == QUIT:
        exit(0)
    with pi.PIHandler() as pih:
        if option == OFF or option == ON:
            for axis in axes:
                pi.set_motor_state(pih,axis,{ON:True,OFF:False}[option])
        if option == HOME or option == SET_POS or option == SET_ANG:
            coordso = {
                axis:pi.get_position(pih,axis) for axis in axes
            }
            if option == HOME:
                print('homing...')
                coords = {pi.X:Xo,pi.Y:Yo}
            if option == SET_POS:
                coords = {}
                for axis in axes:
                    while True:
                        coord = input('enter {} coord (in mm): '.format(axesnamed[axis]))
                        try:
                            coord = float(coord)
                        except ValueError:                            
                            print('coord must be number')
                            continue
                        coords[axis] = coord
                        break
            if option == SET_ANG:
                coords = {}
                while True:
                    angle = input('enter angle (in degs): ')
                    try:
                        angle = float(angle)
                    except ValueError:                            
                        print('angle must be number')
                        continue
                    for axis in axes:
                        coords[axis] = {
                            pi.X:mm.get_xmirr,
                            pi.Y:mm.get_ymirr
                        }[axis](angle,Ro)
                    break
            for axis in axes:
                pi.set_motor_state(pih,axis,True)
                pi.set_position(pih,axis,coords[axis])
            for axis in axes:
                pi.wait_motor(
                    pih,
                    axis,
                    0.25,
                    callback(pih,coords,coordso)
                )
            print('move complete.')
        if option == VEL:
            while True:
                print(
                    'current velocity: {:.2f} mm per sec'.format(
                        pi.get_velocity(pih,pi.X)
                    )
                )
                velocity = input('new velocity (in mm per sec): ')
                try:
                    velocity = float(velocity)
                except ValueError:
                    print('velocity must be number')
                    continue
                break
            for axis in axes:
                pi.set_velocity(pih,axis,velocity)

    
