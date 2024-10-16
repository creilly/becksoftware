from chopper import is_homed
import chopper
import maxon
import argparse

posthresh = 500

OPTION = 'blocking'
BLOCK, UNBLOCK = 'block', 'unblock'

ap = argparse.ArgumentParser(description='utility for blocking/unblocking chopper')
ap.add_argument(OPTION,choices=(BLOCK,UNBLOCK))
blocking = getattr(ap.parse_args(),OPTION)

with maxon.MaxonHandler() as mh:
    print('halting motor')
    chopper.start_halt(mh)
    print('waiting for halt')
    chopper.wait_halt(mh)
    print('halt completed')
    if not maxon.get_homed(mh) or abs(maxon.get_position_act(mh)) > posthresh:    
        print('homing')
        chopper.start_home(mh)
        print('waiting for home')
        chopper.wait_home(mh)    
        print('homing completed')
    print(
        '{} chopper'.format(
            {
                BLOCK:'blocking',
                UNBLOCK:'unblocking'
            }[blocking]
        )
    )
    chopper.set_blocking(
        mh,{
            BLOCK:True,
            UNBLOCK:False
        }[blocking]
    )    
    chopper.wait_movement(mh)
    print(
        'chopper {}'.format(
            {
                BLOCK:'blocked',
                UNBLOCK:'unblocked'
            }[blocking]
        )
    )
