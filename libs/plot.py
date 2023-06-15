from matplotlib import pyplot as plt
import numpy as np

POLFOR, POLBACK = +1, -1
RAD, THETA = 0, 1
MIN, MAX = 0, 1
def polar_plot(
    direction=POLBACK,offset=90,ticks=None,
    rlabel=None,tlabel=None,tmin=None,tmax=None,
    rmin=None,rmax=None
):
    fig, ax = plt.subplots(subplot_kw={'projection':'polar'})
    ax.set_theta_direction(direction)
    ax.set_theta_offset(np.deg2rad(offset))
    if ticks is not None:
        ax.set_xticks(np.deg2rad(ticks))
    for label, axis in (
        (rlabel,'y'),(tlabel,'x')
    ):
        if label is not None:    
            getattr(ax,'set_{}label'.format(axis))(label)
    limd = {}        
    for lims, axis in (((tmin,tmax),THETA),((rmin,rmax),RAD)):
        for key, val in zip(('min','max'),lims):            
            if val is not None:
                if axis is THETA:
                    getattr(ax,'set_theta{}'.format(key))(val)
                if axis is RAD:
                    limd['y{}'.format(key)] = val
    ax.set_ylim(**limd)
    return fig, ax