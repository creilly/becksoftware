from transfercavity import transfercavityclient as tcc
import lockin
from time import time
from time import sleep
import topo
import argparse
import numpy as np
from matplotlib import pyplot as plt
import fit
from bologain import bologainclient, bologainserver

bologainclient.set_gain(bologainserver.X1000)

meastime = 0.25 # seconds
df = 1.0
settletime = 2.0 # seconds

def find_peak(deltaf):
    success = True
    with lockin.LockinHandler() as lih:
        def get_lockin(meastime):
            starttime = time()
            X = Y = 0
            n = 0
            while True:
                x, y, _ = lockin.get_xya(lih)
                X += x
                Y += y
                n += 1 
                if time() - starttime > meastime:
                    break
            X /= n
            Y /= n
            return X, Y
        fo = tcc.get_setpoint()
        print('initial setpoint: {:.2f} MHz'.format(fo))
        fs = np.arange(fo-deltaf/2,fo+deltaf/2,df)
        rs = []
        tcc.set_setpoint(fs[0])
        print('settling.')
        sleep(settletime)
        print('done settling.')
        for f in fs:
            tcc.set_setpoint(f)
            x, y = get_lockin(meastime)
            print(
                ', '.join(
                    [
                        '{}: {}'.format(
                            label,'{:.2f} MHz'.format(
                                freq
                            ).rjust(12)
                        ) for label, freq in (
                            (
                                'f start',fs[0],
                            ),(
                                'f current',f,
                            ),(
                                'f end',fs[-1],
                            )
                        )
                    ] + [
                        '{}: {} uV'.format(                            
                            '{} lockin'.format(label),
                            '{: 10d}'.format(int(1e6*z))
                        )
                        for label, z in (
                            ('x',x),('y',y),('r',np.sqrt(x**2+y**2))
                        )
                    ]
                )
            )
            rs.append(np.sqrt(x**2 + y**2))
        tcc.set_setpoint(fo)
        xs = np.array(rs)
        try:
            params, cov = fit.gaussian_fit(fs,xs,*fit.gaussian_guess(fs,xs))
            print('params',params)

            plt.plot(fs,xs,'k+',label='data')
            plt.plot(fs,fit.gaussian(fs,*params),'r--',label='fit')
            plt.xlabel('tcc setpint / MHz')
            plt.ylabel('lock-in signal r / mV')
            plt.legend()
            plt.show()
        except Exception as err:
            print('error!')
            print(repr(err))
            params, cov = None, None
            success = False        
    return success, fs, xs, params, cov

if __name__ == '__main__':
    DELTAF = 200.0
    parser = argparse.ArgumentParser(description='transfer cavity peak finder')
    parser.add_argument(
        '-d','--deltaf',type=float,default=DELTAF,
        help = 'width of scan (MHz)'
    )
    deltaf = parser.parse_args().deltaf
    while True:
        success, fs, xs, params, cov = find_peak(deltaf)
        if success:
            break
        response = input(
            'error during peak find. enter q to quit or new deltaf to change scan range: '
        )
        if not response or response[0].lower() == 'q':
            exit(0)
        deltaf = float(response)
    fmax = params[0]
    print('peak detuning: {:.2f} MHz'.format(fmax))
    print('setting to peak.')
    tcc.set_setpoint(fmax)
    print('done.')
                
    
