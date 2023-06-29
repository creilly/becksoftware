import opo
import linescan
import dfreq
import wavemeter
import topo
from beckutil import print_color
import hitran
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--filename','-f',help='name of lines file')

linefile = ap.parse_args().filename

lines = dfreq.read_lines(linefile)

dw = -0.0068
ic = topo.InstructionClient()
with wavemeter.WavemeterHandler() as wmh:
    for line in lines:
        print_color('red','new line: {}'.format(hitran.fmt_line(line)))        
        wp, pmax, e, m = linescan.set_line(
            line,dw,wmh,opo=False
        )
        opo.add_entry(
            line,e,m,
            ic.get_piezo(),
            ic.get_diode_set_temperature(),
            wp
        )