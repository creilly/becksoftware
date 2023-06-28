import mirrormotion as mm
from bilt import gcp, PI, RS
import numpy as np
import pi
import rotationstage as rs

def set_hwp(cfg,handlerd,hwp_angle,lid_angle):
    pih, rsh = handlerd[PI], handlerd[RS]    
    phicalib = gcp(cfg,'fluence curve','calib angle',float)
    mir_angle_o = gcp(cfg,'scattering','mirror angle',float)
    lid_angle_o = gcp(cfg,'scattering','lid angle',float)
    delta_theta_mirror_lid = mir_angle_o - lid_angle_o

    mir_angle = lid_angle + delta_theta_mirror_lid
    xo = mm.get_xmirr(mir_angle)
    yo = mm.get_ymirr(mir_angle)
    dx, dy = [deltaz(hwp_angle,phicalib) for deltaz in (deltax,deltay)]
    x = xo + dx
    y = yo + dy
    for mirror, pos in ((pi.X,x),(pi.Y,y)):            
        pi.set_position(
            pih,
            mirror,
            pos
        )   
    rs.set_angle(rsh,hwp_angle)           
    for mirror in (pi.X,pi.Y):
        pi.wait_motor(pih,mirror)  
    return dx, dy

# r = 0.83 # mm
# xo = 25.13 # mm
# yo = 40.75 # mm
# phioo = 274.4 # degs

# calib 2023-06-26
# see Z:\Surface\chris\scripts-data\2023\06\25\hwpmirrorcalib\anhmc.py
r = 0.785 # mm
phio = 194.837 # degs

X, Y = 0, 1

def _deltaz(phi,f):
    return r * f(np.deg2rad(phi - phio))

def deltaz(phi,phimaxp,f):
    return _deltaz(phi,f) - _deltaz(phimaxp,f)

def deltax(phi,phimaxp):
    return deltaz(phi,phimaxp,np.cos)

def deltay(phi,phimaxp):
    return deltaz(phi,phimaxp,np.sin)