import linescan as ls
import topo
import os
import emfile
import argparse
import hitran
import tclock

defaultinfile = 'inlines.txt'
defaultoutfile = 'outlines.txt'

ap = argparse.ArgumentParser()
ap.add_argument('-i','--infile',help='filename containing list of lines to optimize',default=defaultinfile)
ap.add_argument('-o','--outfile',help='filename to output optimized lines to',default=defaultoutfile)
ap.add_argument('wavemeteroffset',type=float,help='wavemeter offset (cm-1)')

args = ap.parse_args()

infile = args.infile
outfile = args.outfile
dw = args.wavemeteroffset

ic = topo.InstructionClient()
if os.path.exists(outfile):    
    donelines = [
        htline for htline, *_ in emfile.parse_em_file(outfile)
    ]
    print('outfile already exists!')
    print('found {:d} lines.'.format(len(donelines)))
    print('(q)uit, (c)ontinue, or (s)tart over?')
    response = input('->: ').lower()[0]
    if response == 'q':
        print('quitting.')
        exit()
    elif response == 'c':
        mode = 'a'
    elif response == 's':
        print('are you sure? this will erase the existing outlines file.')
        sure = input(' [y]/n : ')
        if sure and sure.lower()[0] == 'n':
            print('quitting.')
            exit()
        mode = 'w'
    else:
        print('invalid response.')
        print('quitting.')
        exit()
else:
    donelines = []
    mode = 'w'
tclock.disable_lock()
with open(outfile,mode) as f:
    lines = emfile.parse_em_file(infile)
    while True:        
        htline, po, eo, mo = lines.pop(0)                
        print('next line->',hitran.fmt_line(htline))
        if htline in donelines:
            print('line already calibrated. continuing.')
            continue
        if eo < 0 or mo < 0:
            # this indicates that we should use initial 
            # eo and mo recommended by topotools
            emo = None
        else:
            emo = (eo, mo)
        if po < 0:
            po = 15.0        
        wp, pmax, ep, mp = ls.set_line(htline,dw,em=emo,pv=po)
        pp = ic.get_piezo()
        f.write(emfile.fmt_em_line(htline,pp,ep,mp))
        f.flush()
        if lines:
            f.write('\n')
            continue
        break
        