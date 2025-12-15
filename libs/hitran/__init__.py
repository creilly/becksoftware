import os, pandas as pd

CH4, NH3 = 6, 11

ISO_CH4, ISO_CH3D = 1, 3

WNUM, EIN_COEFF, WNUMBECK = 0, 1, 2
root_folder = 'db'
fname = 'line.txt'
HEADER, DATA = 0, 1
def format_path(folders):
    return os.path.join(
        os.path.dirname(__file__),root_folder,*folders
    )
def lookup_line(folders):
    linefile = get_linefile(folders)
    lines = linefile.split('\n')
    dataline = lines[DATA]
    fields = dataline.split('\t')        
    return {
        key:float(fields[key]) for key in (WNUM,EIN_COEFF,WNUMBECK)
    }

def get_linefile(folders):
    path = format_path(list(folders)+[fname])
    with open(path,'r') as f:
        return f.read()
    
def get_notes(folders):
    linefile = get_linefile(folders)
    return [
        l[2:] for l in linefile.split('\n')[2:]
        if l[:2] == '# '
    ]

def ls(folders):
    path = format_path(folders)
    return os.listdir(path)

MOL, ISO, LGQ, UGQ, LLQ, ULQ, W, A, WB, EPP = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
fields = {
    MOL:(0,2),
    ISO:(2,1),
    LGQ:(82,15),
    UGQ:(67,15),
    LLQ:(112,15),
    ULQ:(97,15),
    W:(3,12),
    A:(25,10),
    EPP:(45,10)
}
def format_line(mol,iso,lgq,ugq,llq,ulq):
    return [
        formatters[key](field) for key, field in sorted(
            {
                MOL:mol,
                ISO:iso,
                LGQ:lgq,
                UGQ:ugq,
                LLQ:llq,
                ULQ:ulq
            }.items()
        )
    ]

NBS = chr(0xA0)
SPACE = ' '
QUOTE = '"'
BACKTICK = '`'
def parse_line(rawline):    
    return {
        key:replace_whitespace(rawline[offset:offset+width]) for key, (offset, width) in fields.items()
    }
def replace_whitespace(s):
    return s.replace(SPACE,NBS).replace(QUOTE,BACKTICK)
def undo_replace(s):
    return s.replace(NBS,SPACE).replace(BACKTICK,QUOTE)
def rws(f):
    def g(*args,**kwargs):
        return replace_whitespace(
            f(*args,**kwargs)
        )
    return g
def fmt_line(line):
    if type(line) is dict:
        line = [
            v for k, v in sorted(line.items())
        ]
    return ':'.join(
        [
            x.replace(NBS,' ').replace('`','"')
            for x in line
        ]
    )

froot = 'db'
fname = 'line.txt'
headers = {
    W:'wavenumber (cm-1)',A:'einstein coefficient (s-1)',WB:'measured wavenumber (cm-1)'
}
entries = (W,A,WB)

def update_entry(folders, w, *notes):
    folderpath = format_path(folders)
    path = os.path.join(folderpath,fname)
    with open(path,'r') as f:
        lines = [
            l for l in f.read().split('\n')
            if l
        ]
    lines.extend(fmt_notes(notes))
    htline = lines[DATA]
    fields = htline.split('\t')
    if w is not None:
        fields[WNUMBECK] = str(w)
    lines[DATA] = '\t'.join(fields)
    with open(path,'w') as f:
        f.write('\n'.join(lines))

def fmt_notes(notes):
    return sum(
        [
            ['# {}'.format(subnote) for subnote in note.split('\n')]
            for note in notes
        ],
        start = []
    )                

class LineOverwriteException(Exception): pass    
class NoWBException(Exception): pass
def add_entry(lined, *notes, overwrite = False):
    if WB not in lined: raise NoWBException('no wbeck specified!')
    *folders, wdb, a, wbeck, epp = list(zip(*sorted(lined.items())))[1]    
    folder = os.path.join(os.path.dirname(__file__),froot,*folders)   
    if not os.path.exists(folder):        
        os.makedirs(folder)
    elif not overwrite:
        raise LineOverwriteException(
            'can not overwrite entry {}!'.format(
                fmt_line(folders)
            )
        )    
    path = os.path.join(folder,fname)
    filetxt = '\n'.join(
        [
            '\t'.join(
                headers[key] for key in entries
            ),                
            '\t'.join(
                {W:wdb,A:a,WB:wbeck}[key].replace(NBS,' ') for key in entries
            ),*fmt_notes(notes)
        ]
    )    
    with open(path,'w') as f:
        f.write(filetxt)

@rws
def format_int(j,width):    
    return str(j).rjust(width)
mol_width = 2
def format_mol(mol):
    return format_int(mol,mol_width)
iso_width = 1
def format_iso(iso):
    return format_int(iso,iso_width)
sym_width = 2
@rws
def format_sym(sym):
    return sym.ljust(sym_width)
gq_lmargin = 3
gq_int_width = 2
@rws
def format_gq(gq,mol=CH4,iso=1):
    if mol == CH4 and iso == ISO_CH3D:
        return gq.rjust(15)
    quanta,sym,level = gq
    return ' '*gq_lmargin + ''.join(
        format_int(nu,gq_int_width)
        for nu in quanta
    ) + format_int(level,gq_int_width) + format_sym(sym)
lq_lmargin = 2
lq_rmargin = 5
j_width = 3
lq_level_width = 3
@rws
def format_lq(lq):    
    j,sym,level = lq
    return ' '*lq_lmargin + format_int(j,j_width) + format_sym(sym) + format_int(level,lq_level_width) + ' '*lq_rmargin

formatters = {
    MOL:format_mol,
    ISO:format_iso,
    LGQ:format_gq,
    UGQ:format_gq,
    LLQ:format_lq,
    ULQ:format_lq
}

def parse_gq(raw_gq,mol=CH4,iso=1):
    return gqformatters[mol](raw_gq,iso)

def parse_gq_ch4(raw_gq,iso):    
    if iso == 3:
        return str(raw_gq)
    raw_gq = raw_gq[gq_lmargin:]
    nmodes = 4
    nmode = 0
    quanta = []
    while nmode < nmodes:
        raw_quanta, raw_gq = raw_gq[:gq_int_width], raw_gq[gq_int_width:]
        quanta.append(int(raw_quanta))
        nmode += 1
    quanta = (*quanta,)
    raw_level, raw_gq = raw_gq[:gq_int_width], raw_gq[gq_int_width:]
    level = int(raw_level)
    sym = raw_gq[:sym_width].strip()
    return quanta, sym, level

def parse_gq_nh3(raw_gq,iso):
    nus = tuple(map(int,raw_gq[1:5]))
    ls = tuple(map(int,raw_gq[6:8]))
    l = int(raw_gq[9])
    sym = raw_gq[11:15].strip()
    return (nus,ls,l,sym)

def parse_gq_co2(raw_gq,iso):    
    raw_gq = raw_gq[gq_lmargin+3:]
    nmodes = 5
    nmode = 0
    quanta = []
    while nmode < nmodes:
        raw_quanta, raw_gq = raw_gq[:gq_int_width], raw_gq[gq_int_width:]
        quanta.append(int(raw_quanta))
        nmode += 1
    quanta = (*quanta,)
    return quanta

gqformatters = {
    CH4:parse_gq_ch4,
    NH3:parse_gq_nh3
}

def parse_lq(raw_lq,mol=CH4,iso=1):
    return lqparsers[mol](raw_lq,iso)
def parse_lq_ch4(raw_lq,iso):
    if iso == 3:
        j = int(raw_lq[:3])
        k = int(raw_lq[3:][:3])
        s = raw_lq[6:].strip()
        return j, k, s
    # need to modify to compensate for 
    # irregularities in boudon database    
    raw_lq = raw_lq.strip()
    rawj = ''
    nj = 1    
    while raw_lq[:nj].isdigit():        
        nj += 1      
    nj -= 1 
    j = int(raw_lq[:nj])
    raw_lq = raw_lq[nj:].strip()    
    sym, rawlevel = map(undo_replace,raw_lq.split())
    level = int(rawlevel)
    return (j, sym, level)

def parse_lq_nh3(rlq,iso):
    j = int(rlq[0:2])
    k = int(rlq[2:5])
    l = rlq[5:7].strip()
    rs = rlq[8:11].strip()
    ts = rlq[11:14].strip()
    l, rs, ts = map(undo_replace,(l,rs,ts))
    return (j,k,l,rs,ts)

def parse_lq_co2(raw_lq,iso):
    raw_lq= raw_lq.strip()
    #print(raw_lq)
    branch, rawj= raw_lq.split()
    jp,ef = int(rawj[:-1]),rawj[-1]
    #print('j:',jp,'branch:',branch,'ef:',ef)
    return jp,branch,ef

lqparsers = {
    CH4:parse_lq_ch4,
    NH3:parse_lq_nh3
}
symd = {
    1:'A1',
    2:'A2',
    3:None,
    4:'F1',
    5:'F2'
}
dbcols = ('mol','iso','lgq','ugq','llq','ulq','line')
def get_db(mol):
    root = [format_mol(mol)]
    rows = []
    for r, d, f in os.walk(format_path(root)):
        if fname in f:
            rows.append(r.split('\\')[-6:])
    return pd.DataFrame(
        [[*row,row] for row in rows],columns=dbcols
    )