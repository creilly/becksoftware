import wavemeter as wm

# nm to cm-1
def wl_to_wn(wl):
    return 1e7/wl

def monitor_mode_hop(wmh,wexp,dw,cb,verbose=False):
    W = 0.0
    prevscannum = None
    n = 0    
    while True:
        meas = wm.get_measurement(wmh,wm.FETCH)
        scannum = meas[wm.SCANNUM]                        
        if prevscannum is None:
            prevscannum = scannum
        if scannum > prevscannum:
            W += wl_to_wn(meas[wm.WAVELENGTH])
            n += 1
            prevscannum = scannum
        continuing = cb()        
        if not continuing and n:
            break
    W /= n
    if verbose:
        print(
            '\t,\t'.join(
                '{} : {}'.format(
                    label,'{:.4f} cm-1'.format(w).rjust(15)
                ) for label, w in (
                    (
                        'wexp',wexp
                    ),(
                        'W',W
                    ),(
                        'dw thresh',dw
                    ),(
                        'dw meas',W-wexp
                    )
                )                                    
            )
        )
    if abs(W-wexp) > dw:        
        print('measured w deviates from expected.')
        return False, None
    return True, W