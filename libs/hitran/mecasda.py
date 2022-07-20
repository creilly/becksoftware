import requests
import hitran

root = 'http://vamdc.icb.cnrs.fr/PHP/'

post = 'CH4.php'

rawpayload = 'cb12CH4=12CH4&charac=dip&datatype=linebyline&cs_step=1&fmin={:f}&fmax={:f}&thres=0&cmdSend=Extract'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36',
    'Content-Type': 'text/plain'
}

W, NU_LOW, NU_HIGH, J, B, S, LL, UL, A = 0, 1, 2, 3, 4, 5, 6, 7, 8

def parse_line(rawline):
    rawline = rawline.replace(hitran.NBS,' ')
    line = {}
    line[W] = float(rawline[4:16])
    line.update(
        {
            nu:[
                int(n) for n in rawline[start:start+7].split(' ')
            ] for nu, start in (
                (NU_HIGH,71),(NU_LOW,86)
            )
        }
    )
    jhigh, jlow = [int(rawline[start:start+2]) for start in (98,113)]
    line[J] = jlow
    line[B] = jhigh-jlow    
    line[S] = rawline[116:][:2]
    line.update(
        {
            key:int(rawline[start:start+3]) for key, start in ((UL,104),(LL,119))
        }
    )
    line[A] = float(rawline[26:34])
    return line

def get_lines(w,deltaw):
    wmin = w-deltaw/2
    wmax = w+deltaw/2
    data = {
        key:value for key, value in [
            field.split('=') for field in rawpayload.format(wmin,wmax).split('&')
        ]
    }
    r = requests.post('http://vamdc.icb.cnrs.fr/PHP/CH4.php', data = data)
    url = r.text.split('Extracted line file <A HREF="',1)[-1].split('"')[0]
    r = requests.get(root + url)
    return [
        line.replace(' ',hitran.NBS)
        for line in 
        r.text.split('\n')
        if line
    ]

def find_line(w,deltaw,nulow,nuhigh,j,b,s,ll,ul):    
    lines = get_lines(w,deltaw)
    while lines:
        line = lines.pop()
        lined = parse_line(line)                
        match = all(
            lined[key] == value for key, value in (
                (NU_LOW,nulow),
                (NU_HIGH,nuhigh),
                (J,j),(B,b),(S,s),(LL,ll),(UL,ul)
            )
        )        
        if match:
            return line            
    return None

if __name__ == '__main__':
    w = 3006.265705
    dw = 0.01
    nulow = [0,0,1,0]
    nuhigh = [0,0,2,0]
    ll = 3
    ul = 29
    j = 1
    b = 1    
    for s in ('A1','A2'):
        # print(get_lines(w,dw))
        print(find_line(w,dw,nulow,nuhigh,j,b,s,ll,ul))