import pi

with pi.PIHandler() as pih:
    for axis in (pi.X,pi.Y):
        pi.set_motor_state(pih,axis,False)
