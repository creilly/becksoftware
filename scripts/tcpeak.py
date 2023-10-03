from transfercavity import transfercavityclient as tcc
import lockin
from time import time
from time import sleep
import topo, config
import argparse
import numpy as np
from matplotlib import pyplot as plt
import fit
from bologain import bologainclient, bologainserver
from grapher import graphclient as gc

X, Y, R = 'x', 'y', 'r'

def find_peak(deltaf,df,tau,sens,axis,saving,name):    
    meastime = 10 * tau # seconds
    settletime = 10 * tau # seconds
    success = True
    with lockin.LockinHandler() as lih:
        tau = lockin.set_time_constant(lih,tau)
        lockin.set_sensitivity(lih,sens)
        lid = config.get_lockin_params(lih)
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
        zs = []
        tcc.set_setpoint(fs[0])
        print('settling.')
        sleep(settletime)
        print('done settling.')
        if saving:
            path = gc.add_dataset(
                [*gc.get_day_folder(),'tc peaks'],
                name,
                ('tc setpoint (MHz)','lockin x (v)','lockin y (v)'),
                metadata={
                    'lockin':lid
                }
            )
        for f in fs:
            try:
                tcc.set_setpoint(f)
                x, y = get_lockin(meastime)
                if saving:
                    gc.add_data(path,(f,x,y))
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
                zs.append(
                    {
                        X:x,Y:y,R:np.sqrt(x**2 + y**2)
                    }[axis]
                )            
            except KeyboardInterrupt:
                response = input('interrupt received. [q]uit or [c]ontinue (default)? : ')
                if response and response.lower()[0] == 'q':
                    exit()
                break            
        zs = np.array(zs)
        fs = fs[:len(zs)]
        tcc.set_setpoint(fo)        
        try:
            if np.abs(zs).max() > zs.max():
                sign = -1.0
            else:
                sign = +1.0
            params, cov = fit.gaussian_fit(fs,sign*zs,*fit.gaussian_guess(fs,sign*zs))
            print('params',params)
            plt.plot(fs,1e3*zs,'k+',label='data')
            plt.plot(fs,1e3*sign*fit.gaussian(fs,*params),'r--',label='fit')
            plt.xlabel('tcc setpoint / MHz')
            plt.ylabel('lock-in {} signal (millivolts)'.format(axis))
            plt.title(name)
            plt.legend()
            plt.show()
        except Exception as err:
            print('error!')
            print(repr(err))
            params, cov = None, None
            success = False        
    return success, fs, zs, params, cov

if __name__ == '__main__':
    DELTAF = 200.0 # MHz
    DF = 1.0 # MHz
    TAU = 100e-3 # seconds
    SENS = 100e-3 # volts
    parser = argparse.ArgumentParser(description='transfer cavity peak finder')
    parser.add_argument(
        '-d','--deltaf',type=float,default=DELTAF,
        help='width of scan (MHz)'
    )
    parser.add_argument(
        '-e','--epsilonf',type=float,default=DF,
        help='frequency step increment (MHz)'
    )
    parser.add_argument(
        '-t','--tau',type=float,default=TAU,
        help='lockin time constant (seconds)'
    )    
    parser.add_argument(
        '-s','--sensitivity',type=float,default=SENS,help='lockin sensitivity'
    )
    parser.add_argument(
        '-a','--axis',choices=(X,R),default=R
    )
    parser.add_argument(
        '-b','--bologain',choices=(10,100,200,1000),type=int,default=1000
    )
    parser.add_argument(
        '-v','--save',choices=('y','n'),default='y',help='save data to grapher'
    )
    parser.add_argument(
        '-n', '--name',default='scan',help='name for grapher dataset'
    )
    args = parser.parse_args()
    deltaf = args.deltaf
    df = args.epsilonf
    tau = args.tau
    sens = args.sensitivity
    saving = {'y':True,'n':False}[args.save]
    axis = args.axis
    bologain = args.bologain
    name = args.name
    bologainclient.set_gain(bologain)
    print(
        ','.join(
            [
                '{}: {} {}'.format(
                    label, '{:.2e}'.format(value).rjust(10), units
                ) for label, value, units in (
                    ('delta f',deltaf,'MHz'),
                    ('df',df,'MHz'),
                    ('tau',tau,'MHz')
                )                
            ]
        ),',','axis:',axis
    )    
    while True:
        success, fs, xs, params, cov = find_peak(deltaf,df,tau,sens,axis,saving,name)
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
                
    
