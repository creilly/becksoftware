import linescan as ls
import topo
import os
import emfile
import argparse
import hitran

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
    print('outfile already exists!')    
    print('quitting.')
    exit(1)
with open(outfile,'w') as f:
    lines = emfile.parse_em_file(infile)
    while True:
        htline, po, eo, mo = lines.pop(0)        
        print('next line->',hitran.fmt_line(htline))
        wp, pmax, ep, mp = ls.set_line(htline,dw,em=(eo,mo))
        pp = ic.get_piezo()
        f.write(emfile.fmt_em_line(htline,pp,ep,mp))
        f.flush()
        if lines:
            f.write('\n')
            continue
        break
        