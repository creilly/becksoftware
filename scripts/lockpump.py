import topo, wavemeter as wm, piezo
# import linescan as ls, hitran as ht
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--wavenumber','-w',type=float)
w_hitran = ap.parse_args().wavenumber
if w_hitran is None:
    print('need to specify wavenumber.')
    exit(1)
    htline = ls.line_wizard()
    w_hitran = ht.parse_line(htline)[ht.W]
print(w_hitran)
w_offset_o = -0.005 # cm-1
w_offset = input('enter pump wavemeter offset (default {:.4} cm-1): '.format(w_offset_o))
if w_offset:
    w_offset = float(w_offset)
else:
    w_offset = w_offset_o    

# w_hitran = 3048.153318 # R(2) F2 v3
# w_hitran = 3067.300026 # R(4) A1 v3
# w_hitran = 2828.092297 # Q(4) A1 ul 3 v2v4
# w_hitran = 2918.483243 # R(4) ul10 E v2v4 # 
# w_hitran = 3067.234 # R(4) E 
# w_hitran = 3067.164189 # R(4) F2 
# w_hitran = 3017.885603 # Q(4) E
# w_hitran = 3028.7522 # R(0) A1 v3


wo = w_hitran + w_offset
damping = 5
dampingp = 10

slope = +0.0928e-2 # cm-1 / volt piezo input

piezo_input_scale = 7.2

coarse_slope = slope * piezo_input_scale # cm-1 / volt piezo output

dw_max = 0.0040 # cm-1

pv_max = dw_max / coarse_slope

dw_thresh = 0.00025 # cm-1

w_min = 2700.0 # cm-1

ic = topo.InstructionClient()

with (
    piezo.PiezoDriverHandler() as pdh,
    wm.WavemeterHandler('argos-wavemeter') as wmh
):
    v = piezo.get_piezo_voltage(pdh,'z') - ic.get_output(topo.B) * piezo_input_scale
    dv = 0  
    try:
        i = 0
        W = None
        while True:
            while True:
                w = wm.get_wavenumber(wmh)
                if w > w_min: break                    
                print('no wavemeter reading...')
            if W is None:
                W = w            
            W = (damping-1) / damping * W + w / damping
            deltaw = W - wo
            if i > damping and abs(deltaw) < dw_thresh: break
            print(
                ', '.join(
                    '{}: {} {}'.format(c,'{:+.4f}'.format(v).rjust(12),u) for c, v, u in zip(
                        ('v','dv','w','d'),
                        (v,dv,W,deltaw),
                        ('volts','volts','cm-1','cm-1')
                    )
                )
            )
            if i > damping:
                dv = -deltaw / coarse_slope / damping / dampingp
                if abs(dv) > pv_max:
                    dv = (+1 if dv > 0 else -1) * pv_max                
                v += dv
                piezo.set_piezo_voltage(pdh,v,'z')                
            i += 1
    except KeyboardInterrupt:
        print('quitting.')
        exit()


def get_b():
    return ic.get_output(topo.B)
with wm.WavemeterHandler('argos-wavemeter') as wmh:
    v = get_b()
    try:
        i = 0
        W = None
        while True:
            w = wm.get_wavenumber(wmh)
            if W is None:
                W = w            
            W = (damping-1) / damping * W + w / damping
            deltaw = W - wo
            print(
                ', '.join(
                    '{}: {} {}'.format(c,'{:+.4f}'.format(v).rjust(12),u) for c, v, u in zip(
                        ('v','w','d'),
                        (v,W,deltaw),
                        ('volts','cm-1','cm-1')
                    )
                )
            )
            if i > damping:
                dv = - deltaw / slope / damping / dampingp
                ic.set_output(topo.B,v + dv)
                v = get_b()
            i += 1
    except KeyboardInterrupt:
        print('quitting.')
