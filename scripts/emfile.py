def read_lines(linefile):
    with open(linefile,'r') as f:
        return [
            parse_line(rawline)
            for rawline in 
            f.read().split('#')[0].split('\n')
            if rawline.strip()
        ]
def parse_line(line):
    return line.split('\t')