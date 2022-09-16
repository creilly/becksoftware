import os
from matplotlib import pyplot as plt
import PIL
import numpy as np
from scipy.optimize import minimize
from beckfile import get_fname
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('folder',help='folder name (e.g. 2022-to analyze. images to analyze must begin with "leed-" (no quotes).')

folder = ap.parse_args().folder

def error(clicks):   
    def _error(params):
        xo, yo, ro = params
        return sum(
            [
                (np.sqrt((x-xo)**2+(y-yo)**2)-ro)**2
                for x, y in clicks
            ]
        )
    return _error

def fit_circle(clicks):
    *clicks, clicko = clicks
    xo, yo = clicko
    ro = sum(
        [
            np.sqrt((x-xo)**2+(y-yo)**2)        
            for x, y in clicks
        ]
    ) / len(clicks)
    return minimize(error(clicks),(xo,yo,ro))
i = 0
resultsfolder = os.path.join(folder,'results')
if not os.path.exists(resultsfolder):
    os.mkdir(resultsfolder)
ratios = {}
for f in os.listdir(folder):    
    fname = f.split('.')[0]
    pre, *post = fname.split('-')
    if pre != 'leed':
        continue
    if i:
        plt.cla()
    i += 1
    name = ' '.join(post)
    print(name)
    im = PIL.Image.open(os.path.join(folder,f))    
    plt.imshow(im)
    plt.title(folder + ' | ' + name)
    radii = []
    thetas = np.linspace(0,2 * np.pi,100)
    for i in range(2):
        ref_points = plt.ginput(0,timeout=-1,mouse_add=None)    
        color=plt.plot(*zip(*ref_points),'+',ms=4)[0].get_color()
        fit = fit_circle(ref_points)
        x, y, r = fit.x        
        plt.plot([x],[y],'o',ms=4,mfc='none',color=color)
        plt.plot([x,x+{0:0,1:r}[i]],[y,y+{0:-r,1:0}[i]],':',color=color)
        plt.plot(
            x + r * np.cos(thetas),
            y + r * np.sin(thetas),
            color=color,
            lw=1
        )
        radii.append(r)
    ratio = radii[1]/radii[0]
    ratios[name] = ratio
    plt.title(
        folder + ' | ' + name + 
        '\n' + 
        'ratio: {:.3f}'.format(ratio)
    )
    plt.tight_layout()        
    plt.savefig(get_fname(name,'png',resultsfolder))    
    plt.show()    
with open(os.path.join(resultsfolder,'results.txt'),'w') as f:    
    f.write(
        '\n'.join(
            '\t'.join([key,str(round(ratio,4))])
            for key, ratio in ratios.items()
        )
    )