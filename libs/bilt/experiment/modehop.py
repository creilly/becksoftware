import wavemeter as wm
import notification
from bilt import AWM, gcp

class ModeHopDetected(Exception):
    pass

def check_pump_wavelength(cfg,handlerd):
    if not gcp(cfg,'pump','pumping',bool):
        return
    awmh = handlerd[AWM]
    pumpw = gcp(cfg,'pump','wavenumber',float) # cm-1
    epsilonw = gcp(cfg,'mode hop','error',float) # cm-1
    w = wm.get_wavenumber(awmh,wm.FETCH)
    if abs(w-pumpw) > epsilonw:
        notification.send_notification(
            '\n'.join(
                [
                    'pump laser lost lock!',
                    'w meas: {:.4f} cm-1, w exp: {:.4f} cm-1'.format(w,pumpw)
                ]
            )
        )
        input('pump lost lock! relock and press enter to continue: ')    