import os

WNUM, EIN_COEFF, WNUMBECK = 0, 1, 2
root_folder = 'db'
fname = 'line.txt'
HEADER, DATA = 0, 1
def format_path(folders):
    return os.path.join(
        os.path.dirname(__file__),root_folder,*folders
    )
def lookup_line(folders):
    path = format_path(list(folders)+[fname])
    with open(path,'r') as f:
        linefile = f.read()
    lines = linefile.split('\n')
    dataline = lines[DATA]
    fields = dataline.split('\t')        
    return {
        key:float(fields[key]) for key in (WNUM,EIN_COEFF,WNUMBECK)
    }
def ls(folders):
    path = format_path(folders)
    return os.listdir(path)

MOL, ISO, GLQ, GUQ, LLQ, ULQ, W, A, WB = 0, 1, 2, 3, 4, 5, 6, 7, 8
fields = {
    MOL:(0,2),
    ISO:(2,1),
    GLQ:(82,15),
    GUQ:(67,15),
    LLQ:(112,15),
    ULQ:(97,15),
    W:(3,12),
    A:(25,10)
}
def format_line(mol,iso,glq,guq,llq,luq):
    return [
        formatters[key](field) for key, field in sorted(
            {
                MOL:mol,
                ISO:iso,
                GLQ:glq,
                GUQ:guq,
                LLQ:llq,
                ULQ:luq
            }.items()
        )
    ]

NBS = chr(0xA0)
def parse_line(rawline):    
    return {
        key:rawline[offset:offset+width] for key, (offset, width) in fields.items()
    }
def replace_whitespace(s):
    return s.replace(' ',NBS)
def rws(f):
    def g(*args,**kwargs):
        return replace_whitespace(
            f(*args,**kwargs)
        )
    return g
def fmt_line(line):
    return ':'.join(
        [
            x.replace(NBS,' ')
            for x in line
        ]
    )

froot = 'db'
fname = 'line.txt'
headers = {
    W:'wavenumber (cm-1)',A:'einstein coefficient (s-1)',WB:'measured wavenumber (cm-1)'
}
entries = (W,A,WB)
def add_entry(lined):
    *folders, wdb, a, wbeck = list(zip(*sorted(lined.items())))[1]    
    folder = os.path.join(os.path.dirname(__file__),froot,*folders)   
    if not os.path.exists(folder):        
        os.makedirs(folder)    
    path = os.path.join(folder,fname)
    filetxt = '\n'.join(
        [
            '\t'.join(
                headers[key] for key in entries
            ),                
            '\t'.join(
                {W:wdb,A:a,WB:wbeck}[key].replace(NBS,' ') for key in entries
            )
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
def format_gq(gq):
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
    GLQ:format_gq,
    GUQ:format_gq,
    LLQ:format_lq,
    ULQ:format_lq
}

def parse_lq(raw_lq):
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
    sym, rawlevel = raw_lq.split()
    level = int(rawlevel)    
    return j, sym, level
    # raw_lq = raw_lq.replace(NBS,' ')[lq_lmargin:]
    # j = int(raw_lq[:j_width])
    # raw_lq = raw_lq[j_width:]
    # sym = raw_lq[:sym_width] 
    # raw_lq = raw_lq[sym_width:]   
    # level = int(raw_lq[:lq_level_width])
    return j, sym, level

symd = {
    1:'A1',
    2:'A2',
    3:None,
    4:'F1',
    5:'F2'
}
# conversion between old and new convention
def search_db(mol,iso,glq,guq,b,j,oldsym=None,ll=None,ul=None):    
    folders = [
        formatters[key](field) for key, field in sorted(
            {
                MOL:mol,ISO:iso,GLQ:glq,GUQ:guq
            }.items()
        )
    ]    
    raw_llqs = os.listdir(format_path(folders))
    for raw_llq in raw_llqs:        
        _j, _sym, _level = parse_lq(raw_llq)        
        if _j == j and (
            oldsym is None or symd[oldsym] is None or _sym == symd[oldsym]
        ) and (
            ll is None or ll == _level
        ):
            folders.append(raw_llq)
            raw_ulqs = os.listdir(format_path(folders))
            for raw_ulq in raw_ulqs:
                __j, __sym, __level = parse_lq(raw_ulq)                
                _b = __j - _j
                if _b == b and (
                    ul is None or ul == __level
                ):
                    folders.append(raw_ulq)                    
                    return [folder for folder in folders]
            folders.pop()
    return None

def _lookup_line_old(folders):
    path = format_path(list(folders)+[fname])
    with open(path,'r') as f:
        linefile = f.read()
    lines = linefile.split('\n')
    dataline = lines[DATA]
    fields = dataline.split('\t')        
    return {
        key:float(fields[key]) for key in (WNUM,EIN_COEFF)
    }

if __name__ == '__main__':
    print(ls([]))
    exit()
    mol = 6
    iso = 1

    glq_quanta = (0,0,0,0)
    glq_sym = 'A1'
    glq_level = 1

    glq = (glq_quanta,glq_sym,glq_level)
    
    guq_quanta = (0,0,1,0)
    guq_sym = 'F2'
    guq_level = 1

    guq = (guq_quanta,guq_sym,guq_level)

    llq_j = 0
    llq_sym = 'A1'
    llq_level = 1

    llq = (llq_j,llq_sym,llq_level)

    luq_j = 1
    luq_sym = 'A2'
    luq_level = 3

    luq = (luq_j,luq_sym,luq_level)

    folders = format_line(mol,iso,glq,guq,llq,luq)
    print(lookup_line(folders))
    folders = search_db(mol,iso,glq,guq,R,0,1)
    print(lookup_line(folders))    