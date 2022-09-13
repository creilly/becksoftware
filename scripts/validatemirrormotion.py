import pi
import mirrormotion as m
import gentec
from grapher import graphclient as gc
import topo
import argparse
import numpy as np
from time import sleep, time
from lid import lidclient

folder = 'mirror validation'

thetamin = 50 # degrees
thetamax = 90
deltatheta = 1.0

waittime = 2.0 # seconds
meastime = 2.0

r = 15.0

path = gc.add_dataset(
    gc.get_day_folder() + [folder],
    'mv',
    (
        'lid angle (degrees)',
        'transmitted power (watts)',
        'ir photodiode (volts)',
        'x mirror position (mm)',
        'y mirror position (mm)'
    ),
    m.get_calibration_metadata()
)

thetas = np.arange(thetamin,thetamax,deltatheta)

ic = topo.InstructionClient()
with (
    pi.PIHandler() as pih,
    gentec.GentecHandler() as pm
):
    for theta in thetas:
        lidclient.set_lid(theta,True)
        x = m.get_xmirr(theta,r)
        y = m.get_ymirr(theta,r)
        for axis, pos in zip((pi.X,pi.Y),(x,y)):
            pi.set_position(pih,axis,pos)
        for axis in (pi.X,pi.Y):
            pi.wait_motor(pih,axis)
        sleep(waittime)
        starttime = time()
        power = 0
        pd = 0
        n = 0
        while True:
            power += gentec.get_power(pm)
            pd += ic.get_input(topo.FAST4)
            n += 1
            if time() - starttime > meastime:
                break
        power /= n
        pd /= n

        gc.add_data(path,(theta,power,pd,x,y))