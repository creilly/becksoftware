import hitran

MOL, LINE, PIEZO, EM, SKIPPING = 0,1,2,3,4
SKIP, NOTSKIP = 1,0
# parse em file for ch4 hot band transitions
n_hitranfields = 6
def parse_em_file(em_file):
    lines = []
    with open(em_file,'r') as f:
        while True:
            line = f.readline().split('#')[0].split('\n')[0]
            if not line.strip():
                return lines
            rawfields = line.split('\t')            
            hitranline, rawfields = rawfields[:n_hitranfields], rawfields[n_hitranfields:]
            piezo = float(rawfields[0])
            etalon = int(rawfields[1])
            motor = float(rawfields[2])            
            lines.append(
                (hitranline,piezo,etalon,motor)
            )
def fmt_em_line(htline,piezo,etalon,motor):
    return '\t'.join(htline + [str(x) for x in [piezo,etalon,motor]])