import numpy as np
from scipy.interpolate import UnivariateSpline, BSpline
import os

# ko, fsr, eo, dphide, no = 'ko', 'fsr', 'eo', 'dphide', 'no'
# model_params = {
#     ko:2.783702e+03,
#     fsr:4.338465e+01,
#     eo:7.388177e+03,
#     dphide:3.532527e-04,
#     no:2.075261e+00
# }

def get_motor(wnum):
    spl = motor_spline(wnum)
    return tuple(
        [
            num / 1000.0 for num in
            (float(motor_spline(wnum)), float(dmotor_spline(wnum)))
        ]
    )

def get_wnum(motor):
    return wnum_spline(motor)

def get_etalon(wnum):
    etalons = []
    for fringenum, ((wmin,wmax),spline) in sorted(etalon_splines.items()):
        if wmax < wnum:
            continue
        if wmin > wnum:
            break
        etalons.append(
            (
                fringenum,
                round(
                    float(
                        spline(
                            wnum
                        )
                    )
                ),
                float(detalon_splines[fringenum][1](wnum))
            )
        )
    return etalons[0][1:]

def _write_spline(fname,spline):
    with open(
        fname,
        'w'
    ) as f:
        f.write(
            '\n'.join(
                '\t'.join(
                    map(
                        '{:e}'.format,
                        row
                    )
                ) for row in (spline.get_knots(),spline.get_coeffs())
            )
        )
        
def _generate_spline(x,y,error=1,smoothing=None):
    return UnivariateSpline(
        x,
        y,
        w=np.ones(len(x))/error,
        s=smoothing*len(x) if smoothing is not None else smoothing
    )

def _load_spline(fname):
    with open(fname,'r') as f:
        knots, coeffs = (
            list(map(float,row.split('\t'))) for row in f.read().split('\n')
        )
        knots = 3*[knots[0]] + knots + 3*[knots[-1]]        
        return BSpline(knots,coeffs,3)

def _load_etalon_splines():
    wbounds = {}
    with open(
        _fmt_etalon_fname(_etalon_bounds_fname,False),
        'r'    
    ) as f:
        wbounds = {
            fringeindex:(wmin,wmax)
            for fringeindex, wmin, wmax in [
                [
                    m(d) for m,d in zip(
                        (int,float,float),
                        line.strip().split('\t')
                    )
                ] for line in f.read().strip().split('\n')[1:] # <-- skip header
            ]            
        }
    return {
        fringenum:(
            wbounds[fringenum],
            _load_spline(
                _fmt_etalon_fname(fringefname,True)
            )
        ) for fringenum, fringefname in [
            (int(fname[-6:-4]),fname)
            for fname in 
            os.listdir(_fmt_etalon_fname('',True))
        ]
    }

def _fmt_fname(fname): return os.path.join(_data_folder,fname)

def _fmt_etalon_fname(fname,infolder):
    return os.path.join(
        *(
            [_data_folder]
            + ([_etalon_splines_folder] if infolder else [])
            + [fname]
        )
    )

_data_folder = os.path.join(os.path.dirname(__file__),'data')
_wnum_spline_fname = 'wnum_spline.dat'
_motor_spline_fname = 'motor_spline.dat'
_wnum_calib_fname = 'wnum-vs-motor.dat'
_etalon_splines_folder = 'etalon splines'
_etalon_bounds_fname = 'fringe_bounds.dat'

wnum_spline = _load_spline(
    _fmt_fname(_wnum_spline_fname)
)
motor_spline = _load_spline(
    _fmt_fname(_motor_spline_fname)
)
dmotor_spline = motor_spline.derivative()
etalon_splines = _load_etalon_splines()
detalon_splines = {key:(bounds,spline.derivative()) for key, (bounds,spline) in etalon_splines.items()}

# for wnum in np.arange(2800,3200,50):
#     print(
#         'wnum:\t{0:d}\tmotor:\t{1:f}\tetalon:\t{2:d}'.format(
#             wnum,
#             get_motor(wnum)/1000,
#             round(float(get_etalon(wnum)[0][1]))
#         )
#     )

if __name__ == '__main__':
    # see also etalonsplines.py in this folder
    # for generation of etalon splines
    from matplotlib import pyplot as plt
    motors, wnums = np.loadtxt(
        _fmt_fname(_wnum_calib_fname)
    ).transpose()
    # smoothing = 1 / 2**1 + 0 / 2**2 + 0 / 2**3 + 1 / 2**4 + 1 / 2**5
    # error = 1.0
    # spline = _generate_spline(motors,wnums,error,smoothing)
    # vvvvvvvvv comment/uncomment below vvvvvvvvvvv
    # check quality of fit
    # m, b = np.polyfit(motors,wnums,1)
    # line = m*motors + b
    # plt.plot(motors,spline(motors)-line,color='blue')
    # plt.scatter(motors,wnums-line,s=1,color='red')
    # plt.show()
    # # check monotonic by plotting derivative
    # plt.plot(motors,spline.derivative()(motors))
    # plt.show()
    # ^^^^^^^^^^ comment/uncomment above ^^^^^^^^^^
    
    # _write_spline(
    #     _fmt_fname(_wnum_spline_fname),
    #     spline
    # )
    
    # vvvvvvvvv comment/uncomment below vvvvvvvvvvv
    # check spline loading from file
    # m, b = np.polyfit(motors,wnums,1)
    # line = m*motors + b
    # plt.scatter(
    #     motors,
    #     _load_spline(
    #         _fmt_fname(_wnum_spline_fname)
    #     )(motors)-line,
    #     s=1,color='green'
    # )
    # plt.scatter(
    #     motors,
    #     wnums-line,
    #     s=1,color='red'
    # )
    # plt.xlabel('motor position (um)')
    # plt.ylabel('wavenumber deviation from linear (cm-1)')
    # plt.title('spline of wavenumber-motor relationship')
    # plt.show()
    # ^^^^^^^^^^ comment/uncomment above ^^^^^^^^^^
    # motors = np.linspace(motors.min(),motors.max(),len(motors))
    # wnums = spline(motors)
    # spline = _generate_spline(
    #     wnums,
    #     motors,
    #     1,
    #     0 / 2**0 + 0 / 2**1 + 0 / 2**2 + 0 / 2**3 + 0 / 2**4 + 0 / 2**5
    # )

    # _write_spline(
    #     _fmt_fname(_motor_spline_fname),
    #     spline
    # )
    
    # vvvvvvvvv comment/uncomment below vvvvvvvvvvv
    # # check spline loading from file
    m, b = np.polyfit(wnums,motors,1)
    line = m*wnums + b
    plt.plot(
        wnums,
        motors-line,
        '.',
        color='blue'
    )
    plt.plot(
        wnums,
        _load_spline(
            _fmt_fname(_motor_spline_fname)
        )(wnums)-line,color='green'
    )
    plt.ylabel('motor position deviation from linear (um)')
    plt.xlabel('wavenumber (cm-1)')
    plt.title('inverted spline of wavenumber-motor relationship')
    plt.show()
    # ^^^^^^^^^^ comment/uncomment above ^^^^^^^^^^
