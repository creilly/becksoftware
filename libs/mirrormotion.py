import numpy as np
import pi

# the module includes the mirror motion and comunication with the pi stages



# r =	 15.438000000010094 # - circle radius (mm)
# xc =	-31.319999999953822  #x offset (mm)
# yc =	-35.85999999995311 # - y offset (mm)
# a =	 -7.200000000006241  #- angle offset (degs)
# e=	0.996000000000012 # -squish (unitless)
# s = 0.7499999999935891 #- slant (degs)



# # latest calibration data: 21/12/2021, analyzed AND UPDATED 03/01/2021

# xc = -35.19999999995426     #x offset (mm)
# yc = -33.29999999995271     #y offset (mm)
# r = 15.590000000010145      # - circle radius (mm)
# a = -9.050000000006188      #- angle offset (degs)
# e = 1.0260000000000002      # -squish (unitless)
# s = -2.0000000000063523     #- slant (degs)

    
# latest calibration data: 05/01/2022, analyzed AND UPDATED 06/01/2022

calibdate = '2022.01.05'

ro = 16.0

xc = -25.812800000141785     #x offset (mm)
yc = -39.51900000014259     #y offset (mm)
r = 14.962259999773522      # - circle radius (mm), calibrated at r=15.0
a =  -5.603500000056165      #- angle offset (degs)
e = 1.010219999972917      # -squish (unitless)
s = -1.910800000003037     #- slant (degs)

def get_calibration_metadata():
    return {
        'calibration parameters':{
            'xc':xc,
            'yc':yc,
            'r':r,
            'a':a,
            'e':e,
            's':s
        },
        'calibration date':calibdate
    }

def get_xmirr(A,r=ro):
    xo  =   r * e * np.cos((A + a)*np.pi/180.)
    yo  =   r / e * np.sin((A + a)*np.pi/180.)
    x   =   xc + np.cos(s*np.pi/180.) * xo + np.sin(s*np.pi/180.) * yo
    return -x
	
def get_ymirr(A,r=ro):
    xo  =   r * e * np.cos((A + a)*np.pi/180.)
    yo  =   r / e * np.sin((A + a)*np.pi/180.)
    y 	= 	yc + np.cos(s*np.pi/180.) * yo - np.sin(s*np.pi/180.) * xo
    return -y

def move_pi(handle,axis,position):
    pi.set_position(handle,axis,position)
    pi.wait_motor(handle,axis)

def set_mirrors(handle,angle,wait=True,r=ro):
    pi.set_position(handle,pi.X,get_xmirr(angle,r))
    pi.set_position(handle,pi.Y,get_ymirr(angle,r))
    if wait:
        wait_mirrors(handle)

def wait_mirrors(handle):
    pi.wait_motor(handle,pi.X)
    pi.wait_motor(handle,pi.Y)
    
if __name__ == '__main__':
    with pi.PIHandler() as pih:
        axisd = {
        pi.X:'x',
        pi.Y:'y'
        }
        for axis in (pi.X,pi.Y):
            print('turning motor {} on'.format(axisd[axis]))
            pi.set_motor_state(pih,axis,True)              
        x = pi.get_position(pih,pi.X)
        print('x initial position: {}'.format(x))
        y = pi.get_position(pih,pi.Y)
        print('y initial position: {}'.format(y))
    
        while True:
            phi_p = input('enter desired angle (in degrees, or enter to quit): ')
            if phi_p:
                set_mirrors(pih,float(phi_p))
                continue
            break
            
