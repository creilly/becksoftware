import numpy as np
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit

fname = 'topoprofile.txt'

image = np.loadtxt(fname,skiprows=4)

xmin = 180
xmax = 300

ymin = 326
ymax = 440

coords = []
pixels = []

pixelcutoff = 16000
for y in range(ymin,ymax):
    for x in range(xmin,xmax):
        pixel = image[y][x]
        if pixel < pixelcutoff:
            continue
        coords.append((x-xmin,y-ymin))
        pixels.append(pixel)

def gaussian(x,y,a,b,c,xo,yo):
    return a * np.exp(
        -1/2*(
            (x-xo)**2 + (y-yo)**2
        ) / b**2
    ) + c

def fit(coords,*args):
    pixels = []
    for coord in coords:
        x, y = coord
        pixels.append(gaussian(x,y,*args))
    return pixels

xo = 56
yo = 50.5
pmax = 23000
pmin = 17000
fwhm = 44
umperpix = 17

guess = (
    pmax - pmin, fwhm / 2.355, pmin, xo, yo
)
params, cov = curve_fit(fit,coords,pixels,guess)
print(guess)
print(params)
a,b,c,xo,yo = params
print('sigma',b*umperpix)
print('1/e2 radius',b*2*umperpix)
xfit = np.arange(xmax-xmin)
yfit = np.arange(ymax-ymin)
Xfit, Yfit = np.meshgrid(xfit,yfit)
xfit *= umperpix
yfit *= umperpix
Zfit = gaussian(Xfit,Yfit,*params)-c
plt.contour(Xfit*umperpix,Yfit*umperpix,Zfit,cmap='Greys')
plt.pcolor(xfit,yfit,image[ymin:ymax,xmin:xmax]-c,vmin = Zfit.min(),vmax = Zfit.max(),cmap='Greys')
plt.colorbar()
plt.xlabel('horizontal axis (um)')
plt.ylabel('vertical axis (um)')
plt.title('topo idler profile')
plt.show()
