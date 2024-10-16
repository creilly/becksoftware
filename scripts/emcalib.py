import linescan, opo, topo, emfile, \
    argparse, hitran, tclock, wavemeter as wm, \
        beckutil

defaultinfile = 'inlines.txt'
defaultoutfile = 'outlines.txt'

ap = argparse.ArgumentParser()
ap.add_argument('listfile',help='path to line list')
ap.add_argument('wavemeteroffset',type=float,help='wavemeter offset (cm-1)')

args = ap.parse_args()

listfile = args.listfile
dw = args.wavemeteroffset

ic = topo.InstructionClient()
tclock.disable_lock()
with wm.WavemeterHandler() as wmh:
    while True:
        with open(listfile,'r+') as f:    
            if '#' in f.read():
                f.seek(0)
                index = None
                while True:
                    line = f.readline()
                    if not line: break
                    if line[0] == '#':
                        index = f.tell() - len(line) - 1
                    else:
                        if index is not None:
                            break
            else:
                f.seek(0)
                index = 0
                line = f.readline()
            if not line:
                beckutil.print_color('blue','calib finished.')
                break
            htline = emfile.parse_line(line[:-1])
            beckutil.print_color('blue','next line->',hitran.fmt_line(htline))
            w, pd, e, m = linescan.set_line(
                htline,dw,wmh,opo = True
            )
            pv = ic.get_piezo()
            dt = ic.get_diode_set_temperature()
            opo.add_entry(htline,e,m,pv,dt,w)
            beckutil.print_color('blue','line completed.')
            tail = f.read()
            f.seek(index)
            f.write(
                line + '#\n' + tail
            )