import lockin, config, numpy as np, argparse, interrupthandler, maxon, chopper, time
from bologain import bologainserver, bologainclient
from lid import lidclient
from grapher import graphclient as gc

fo = 237.0 # Hz
foldero = 'lid scans'

ap = argparse.ArgumentParser()

ap.add_argument(
    '-l','--laser',action='store_true',help='laser measurement (no molecular beam chopper)'
)
ap.add_argument(
    '-b','--bologain',type=int,
    choices=(
        bologainserver.X10,
        bologainserver.X100,
        bologainserver.X200,
        bologainserver.X1000,
    ),
    default=bologainserver.X1000,help='bolometer gain'
)
ap.add_argument(
    'start',type=float,help='starting lid angle'
)
ap.add_argument(
    'stop',type=float,help='final lid angle'
)
ap.add_argument(
    'step',type=float,help='lid angle step size'
)
ap.add_argument(
    'name',help='dataset name'
)
ap.add_argument(
    '-t','--tau',type=float,help='lockin time constant (seconds)'
)
ap.add_argument(
    '-v','--sensitivity',type=float,help='lockin sensitivity'
)
ap.add_argument(
    '-f','--frequency',type=float,default=fo,help='chopper frequency (Hz). default {:.1f} Hz'.format(fo)
)
ap.add_argument(
    '-d','--folder',default=foldero,help='grapher folder (default "{}")'.format(foldero)
)
ap.add_argument(
    '-r','--rootfolder',nargs='*',help='root folder tree. separate levels by space. default is day folder.'
)
ap.add_argument(
    '-i','--info',help='info to add to metadata'
)

args = ap.parse_args()

if args.bologain is not None:
    bologainclient.set_gain(args.bologain)

with lockin.LockinHandler() as lih:
    for arg, func in (
        (args.tau, lockin.set_time_constant),
        (args.sensitivity, lockin.set_sensitivity),
    ):
        if arg is not None:
            func(lih,arg)
    tau = lockin.get_time_constant(lih)

measure_time = tau * 20

freq = args.frequency

with maxon.MaxonHandler() as mh:
    try:
        angles = np.arange(args.start,args.stop,args.step)
        print('press ctrl-c to quit.')
        print('starting lid move')
        lidclient.set_lid(angles[0]-0.001,wait=False)
        if not args.laser:
            print('starting spin')
            chopper.start_spin(mh,freq*60/2)
            print('waiting spin...')
            chopper.wait_spin(mh,1.0)
            print('spin done.')            
        print('waiting lid move...')
        lidclient.wait_lid()
        print('lid move done')
        with (
            lockin.LockinHandler() as lih,
            interrupthandler.InterruptHandler() as ih,
        ):
            if lockin.get_unlocked(lih):                
                print('waiting for lockin to lock...')        
                while lockin.get_unlocked(lih):
                    continue
                print('lockin locked.')
            folder = [*(gc.get_day_folder() if args.rootfolder is None else args.rootfolder),args.folder]
            metadata = {} if args.info is None else {'info':args.info}
            metadata.update(config.get_metadata(lih,[config.LOGGER,config.LOCKIN,config.BOLOMETER]))
            path = gc.add_dataset(
                folder,
                args.name,
                (
                    'lid angle (degrees)',
                    'lockin r (volts)',
                    'lockin theta (degrees)'            
                ),
                metadata = metadata
            )
            for angle in angles:
                if ih.interrupt_received():
                    print('interrupt received. quitting.')
                    break
                lidclient.set_lid(angle)                
                lidclient.wait_lid()
                print('angle set: {:.2f} degs'.format(angle))
                to = time.time()
                while time.time() - to < measure_time:
                    if ih.interrupt_received():
                        print('interrupt received. quitting.')
                        break
                r, t = lockin.get_rt(lih)
                n = 0                                
                gc.add_data(path,(angle,r,t))
    finally:
        if not args.laser:
            print('halting...')
            chopper.start_halt(mh)
            chopper.wait_halt(mh,1.0)
            print('halted.')
            print('homing...')
            chopper.start_home(mh)
            chopper.wait_home(mh,1.0)
            print('homed.')
            print('blocking...')
            chopper.set_blocking(mh,True)        
            chopper.wait_movement(mh,1.0)
            print('blocked.')