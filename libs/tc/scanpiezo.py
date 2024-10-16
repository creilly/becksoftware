from scanner import Scanner
from fitter import Fitter, get_eta, get_ir_fit
import time, daqmx, numpy as np
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.optimize import curve_fit
from grapher import graphclient as gc

freqmod = True
deltav = 8
epsilon = 0.4
deltat = 0.04
buffer = 0.20
samplingrate = 200e3

with (
    daqmx.TaskHandler('transfer cavity piezo task',global_task=True) as aot,
    daqmx.TaskHandler('transfer cavity detector task',global_task=True) as ait,
    daqmx.TaskHandler('transfer cavity dummy trigger',global_task=True) as cot,
    daqmx.TaskHandler('transfer cavity frequency task',global_task=True) as cit,
):
    scanner = Scanner(
        aot,ait,cot,cit,samplingrate,deltat,deltav,epsilon,buffer,freqmod
    )
    fitters = {
        direction:Fitter(scanner.margined_ramps[direction])
        for direction in (scanner.UP,scanner.DOWN)
    }

    ## plotting prep

    nfits = 1000
    fitetas = np.linspace(
        -6, +6, nfits
    )
    scatters, lines = [], []
    for direction in (scanner.UP, scanner.DOWN):        
        scatter = plt.plot(
            scanner.decimated_ramps[direction],
            np.zeros(len(scanner.decimated_ramps[direction])),            
            '.',ms=2,color={
                0:'black',1:'red'
            }[direction]
        )[0]
        scatters.append(scatter)
        line = plt.plot(
            fitetas,np.zeros(nfits),color=scatter.get_color()
        )[0]
        lines.append(line)

    plt.ylim(ymin=-0.05,ymax=+0.6)    
    plt.gcf().set_size_inches(10,7)    

    scans = 20    
    direction_scalars = {
        scanner.UP:3.0,scanner.DOWN:1.0
    }
    path = gc.add_dataset(
        [*gc.get_day_folder(),'lamb dip monitor'],
        'monitor',
        ('time (minutes)','argos tc freq (MHz)','topo tc freq (MHz)')
    )
    to = time.time()
    fs = {
        direction:(
            0,0
        ) for direction in (scanner.UP,scanner.DOWN)
    }
    nscans = 125
    def loop(count):                            
        for _ in range(2):       
            d, data = scanner.read(scanner.scan_samps)                    
            if data is None or data[scanner.INDEX] < scans: 
                # fs[d] = 0.
                continue
            henedata, irdata = [
                data[scanner.MARGNINED][channel]
                for channel in scanner.channels
            ]
            fitters[d].update_hene(henedata)
            fitters[d].update_ir(irdata)
            scatter = scatters[d]
            line = lines[d] 
            scatter.set_xdata(get_eta(scanner.decimated_ramps[d],*fitters[d].etaparams))
            scatter.set_ydata(    
                direction_scalars[d] *             
                data[scanner.DECIMATED][scanner.channels[1]]
            )            
            line.set_ydata(            
                direction_scalars[d] *     
                get_ir_fit(
                    *fitters[d].ircalib
                )(
                    fitetas,fitters[d].f
                )
            )                       
            count, fsum = fs[d]
            fsum += fitters[d].f
            count += 1
            fs[d] = (count,fsum)
            if all(
                count > 250
                for count, fsum in fs.values()
            ):
                gdata = [(time.time() - to)/60]
                for direction in (
                    scanner.UP, scanner.DOWN
                ):
                    count, fsum = fs[direction]
                    gdata.append(
                        fsum / count
                    )
                    fs[direction] = (0,0)
                gc.add_data(path,gdata)        
        return [*scatters,*lines]        
    
    animation = FuncAnimation(plt.gcf(),loop,interval=1)    
    scanner.set_scanning(True)
    plt.show()    
    scanner.set_scanning(False)    