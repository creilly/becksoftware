import numpy as np

r = 0.83 # mm
xo = 25.13 # mm
yo = 40.75 # mm
phioo = 274.4 # degs

xbar = 25.00 # mm
ybar = 40.00 # mm

phimaxo = 7.5 # degrees

X, Y = 0, 1

def _deltax(phi,phimaxp):
    phiop = phioo + (phimaxp-phimaxo)
    return xo - xbar + r * np.cos(
        np.deg2rad(phi - phiop)
    )

def deltax(phi,phimaxp):
    return _deltax(phi,phimaxp) - _deltax(phimaxp,phimaxp)

def _deltay(phi,phimaxp):
    phiop = phioo + (phimaxp-phimaxo)
    return yo - ybar + r * np.cos(
        np.deg2rad(phi + 90.0 - phiop)
    )

def deltay(phi,phimaxp):
    return _deltay(phi,phimaxp) - _deltay(phimaxp,phimaxp)

if __name__ == '__main__':
    from grapher import graphclient as gc
    from matplotlib import pyplot as plt
    folder = ['2022','05','25','hwpdisp']

    datasets, folders, metadatas = gc.get_dir(folder)

    phid = {}

    phimax = 280
    
    for dataset, metadata in zip(datasets,metadatas):
        metadata = gc.get_metadata(folder + [metadata])

        phi = metadata['phi'][0]
        if phi > phimax:
            continue

        axis = Y if 'x' in metadata else X
            
        zs, ps = gc.get_data_np(folder + [dataset])
        zmax = zs[ps.argmax()]

        phid.setdefault(phi,{})[axis] = zmax

    xs = []
    ys = []
    phis = []

    for phi, d in phid.items():
        phis.append(phi)
        xs.append(d[X])
        ys.append(d[Y])

    for zs, axis, label in (
        (xs,X,'x'),(ys,Y,'y')
    ):
        plt.plot(phis,zs,'.',label='data')

        fitphis = np.linspace(min(phis),max(phis),200)
        plt.plot(
            fitphis,
            [{X:deltax,Y:deltay}[axis](phi)+{X:xbar,Y:ybar}[axis] for phi in fitphis],
            label='fit'
        )

        plt.xlabel('half wave plate angle (degs)')
        plt.ylabel('{} mirror position (mm)'.format(label))
        plt.title('rotation stage displacement calibration - {} mirror'.format(label))
        plt.legend()        
        plt.show()