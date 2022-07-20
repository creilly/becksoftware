import rotationstage as rot

sn = None
try:
    sn = rot.open_device()
    if not rot.is_homed(sn):
        print('motor not homed')
        while True:
            home = input('home motor? (y/n): ').lower()                
            if home == 'y':
                print('homing motor...')
                rot.home(sn)
                break
            if home == 'n':
                raise Exception('motor not homed')
            else:
                print('please enter y or n')
    angle = rot.get_angle(sn)
    print('current angle: {:.3f} degrees'.format(angle))
    while True:
        try:
            angle = float(input('angle to set: '))
            break
        except ValueError:
            print('please enter a numeric value')
    print('setting angle to {:.3f} degrees...'.format(angle))
    rot.set_angle(sn,angle)
    angle = rot.get_angle(sn)
    print('angle now {:.3f} degrees'.format(angle))
finally:
    if sn is not None:
        rot.close_device(sn)
