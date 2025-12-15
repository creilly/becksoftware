import piezo, topo, msvcrt, sys, wavemeter621

while True:
    try:
        wtarget = float(input('enter target w: '))
        break
    except ValueError:
        continue

topo_channel = topo.B
piezo_channel = 'z'
piezo_input_scale = 7.2

wm = True

Vmin = 0
Vmax = 60
vmin = 0.5
vmax = 3.5

DV1000MV, DV100MV, DV10MV, DV1MV = 1000, 100, 10, 1
PIEZO, TOPO = 0, 1

ic = topo.InstructionClient()
if wm:
    WMH = wavemeter621.Bristol621Handler
else:
    class WMH:
        def __enter__(self):
            return None
        def __exit__(self,*args):
            pass
with (
    piezo.PiezoDriverHandler() as pdh,
    WMH() as wmh
):
    v = ic.get_output(topo_channel)
    V = piezo.get_piezo_voltage(pdh) - v * piezo_input_scale
    for uc, dc, dv, ch in (
        ('q','a',DV1000MV,PIEZO),
        ('w','s',DV100MV,PIEZO),
        ('e','d',DV10MV,PIEZO),
        ('r','f',DV10MV,TOPO),
        ('t','g',DV10MV,TOPO)
    ):
        print(
            '{}/{}: +/- {} v {}'.format(
                uc, dc, {
                    DV1000MV:'1',
                    DV100MV:'0.1',
                    DV10MV:'0.01',
                    DV1MV:'0.001'
                }[dv], {
                    PIEZO:'piezo',TOPO:'topo'
                }[ch]
            )
        )
    print('Q: quit')
    while True:
        if wmh is not None:
            w = wmh.get_wavenumber()
        else:
            w = 0.0
        dw = wtarget - w
        sys.stdout.write(
            '\r{}: '.format(
                ', '.join(
                    [
                        '{{:+.{:d}f}} {} {}'.format(nd,unit,ch).format(v).rjust(nc)
                        for v, nd, nc, unit, ch in (
                            (V + v * piezo_input_scale, 3, 8, 'v', 'p'),
                            (v, 4, 8, 'v', 't'),
                            (w, 5, 15, 'cm-1', 'wm'),
                            (dw, 5, 15, 'cm-1', 'wm')
                        )
                    ]
                )
            )
        )
        sys.stdout.flush()        
        if msvcrt.kbhit():
            try:
                c = msvcrt.getch().decode('utf8')
            except UnicodeDecodeError:
                continue
            # sys.stdout.write(c + '\n')
            if c == 'Q':
                exit()
            if c not in 'qawsedrftg':
                break                
            s = +1 if c in 'qwert' else -1
            if c in 'qa': dv = 1.0
            if c in 'ws': dv = 0.1
            if c in 'edrf': dv = 0.01
            if c in 'tg': dv = 0.001
            if c in 'qawsed':
                V = max(Vmin,min(Vmax,V + s*dv))
                piezo.set_piezo_voltage(pdh,V,piezo_channel)
            if c in 'rftg':
                v = max(vmin,min(vmax,v + s*dv))
                ic.set_output(topo_channel,v)