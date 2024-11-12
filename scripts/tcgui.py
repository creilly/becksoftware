import tkinter as tk, tc.tcclient as tcc, numpy as np, threading, time
from tc.scanner import Scanner as S
from tc import tcserver as tcs, fitter
from argparse import ArgumentParser as AP

ap = AP(description='transfer cavity gui client')
ap.add_argument('--direction','-d',choices=(S.UP,S.DOWN))

ww = 900
wh = 900
cw = 750
ch = 300

direction = ap.parse_args().direction

buffer = 0.05

HENE, IR = tcs.HENE, tcs.IR
TOPO, ARGOS = 'topo', 'argos'
FREQ = 'freq'
laser = {
    S.DOWN:TOPO,
    S.UP:ARGOS
}[direction]

vmins = {
    HENE:-0.05,
    IR:-0.05,
    FREQ:-100.0
}

vmaxs = {
    HENE:+0.15,
    IR:{
        TOPO:+0.55,
        ARGOS:+0.20
    }[laser],
    FREQ:+100.0
}

SCANNING, FITTING, LOCKING = 'scanning', 'fitting', 'locking'

VMIN, VMAX = 'V min', 'V max'

FREQUENCY, SETPOINT = 'frequency', 'setpoint'

FMAX, FMIN = 'f max', 'f min'

properties = (SCANNING, FITTING, LOCKING, FREQUENCY)

# setup
window = tk.Tk()
window.geometry('x'.join(map(str,(ww,wh))))
window.title('transfer cavity')

# canvas 
canvas = tk.Canvas(window, width=cw, height=ch, bg = 'white')
row = 0
canvas.grid(row=row,column=0,columnspan=4,padx=15)
row += 1

fmin = -10
fmax = +10
history = 1500
freqs = [None] * history

vsetters = {}

def create_plot_controls(channel, units):
    column = 0    
    for vlimit in (VMIN,VMAX):
        tk.Label(
            window,
            text='{} {} ({})'.format(
                {HENE:'hene',IR:laser,FREQ:'freq'}[channel],{
                    VMIN:'min', VMAX:'max'
                }[vlimit],units
            )
        ).grid(row=row,column=column)
        column += 1        
        stringvar = tk.StringVar(
            window,
            value=str(
                round(
                    {
                        VMIN:vmins,VMAX:vmaxs
                    }[vlimit][channel],3
                )
            )
        )
        vsetters[(channel,vlimit)] = stringvar        
        tk.Entry(
            window,textvariable=stringvar            
        ).grid(row=row,column=column)        
        column += 1
for channel in (HENE,IR):
    create_plot_controls(channel,'v')
    row += 1

pgetters = {}
for property in (SCANNING,FITTING,LOCKING):    
    tk.Label(window,text=property).grid(row=row,column=0)    
    pgetter = tk.Label(window,text='none')
    pgetter.grid(row=row,column=1)    
    pgetters[property] = pgetter
    intvar = tk.IntVar()
    psetter = tk.Checkbutton(window,variable=intvar)
    psetter.grid(row=row,column=2)        
    def get_command(intvar,function,args):
        def command():
            start_thread(
                lambda *_: None,
                function,
                *args,bool(intvar.get())
            )
        return command
    tk.Button(
        window,text='set',command=get_command(
            intvar, {
                SCANNING:tcc.set_scanning,
                FITTING:tcc.set_fitting,
                LOCKING:tcc.set_locking
            }[property], [] if property == SCANNING else [direction]
        )
    ).grid(row=row,column=3)
    row += 1

freqframe = tk.Frame(window)
freqframe.grid(row=row,column=0,columnspan=4,sticky='W',pady=5)
row += 1
frow = 0
fcol = 0
tk.Label(freqframe,text='frequency',width=8).grid(row=frow,column=fcol,padx=5)
fcol += 1
tk.Label(freqframe,text='measured:',width=10).grid(row=frow,column=fcol,padx=5,sticky='E')
fcol += 1
freqlabel = tk.Label(freqframe,text='none',width=20,font='courier')
freqlabel.grid(row=frow,column=fcol)
fcol += 1
tk.Label(freqframe,text='setpoint:',width=10).grid(row=frow,column=fcol,padx=5,sticky='E')
fcol += 1
setpointlabel = tk.Label(freqframe,text='none',width=20,font='courier')
setpointlabel.grid(row=frow,column=fcol)
fcol += 1
setpointvar = tk.StringVar(freqframe,value='none')
setpointentry = tk.Entry(freqframe,textvariable=setpointvar,width=8).grid(row=frow,column=fcol)
fcol += 1
def setpoint_cb():
    raw_setpoint = setpointvar.get()
    try:
        setpoint = float(raw_setpoint)
    except ValueError:
        print('error parsing setpoint: "{}"'.format(raw_setpoint))
    start_thread(lambda *_: None,tcc.set_setpoint, direction, setpoint, wait=False)
tk.Button(freqframe,text='set',command=setpoint_cb).grid(row=frow,column=fcol,padx=5)

create_plot_controls(FREQ,'mhz')
row += 1

# canvas 
freqcanvas = tk.Canvas(window, width=cw, height=ch, bg = 'white')
freqcanvas.grid(row=row,column=0,columnspan=4,padx=15)
row += 1

tk.Button(
    window,
    text='zero offset',
    command=lambda: start_thread(
        lambda _: None,
        tcc.zero_offset,
        direction
    )
).grid(
    row=row,column=0
)
row += 1

colord = {HENE:'red',IR:'blue'}
fitcolord = {HENE:'orange',IR:'green'}

vmin = -4.0
vmax = +4.0
Vmin = -0.05
Vmax = +0.75

def scale(alpha,alphamin,alphamax,betamin,betamax):
    return betamin + (betamax-betamin) * (
        alpha - alphamin
    ) / (alphamax - alphamin)
def vscale(v):
    return scale(v,vmin,vmax,cw*buffer,cw*(1-buffer))
def Vscale(V):
    return scale(V,Vmin,Vmax,ch*(1-buffer),ch*buffer)
def nscale(n):
    return scale(n,0,history,cw*buffer,cw*(1-buffer))
def fscale(f):
    return scale(f,fmin,fmax,ch*(1-buffer),ch*buffer)

def update_limits(channel):    
    for vlimit in (VMIN, VMAX):
        rawlimit = vsetters[channel,vlimit].get()
        try:
            limit = float(rawlimit)
        except ValueError:
            print('invalid input {} {}: "{}"'.format(channel,vlimit,rawlimit))
            return
        {
            VMIN:vmins,VMAX:vmaxs
        }[vlimit][channel] = limit

def plot(channel,arr):
    update_limits(channel)
    coords = np.vstack(
        (
            vs_scaled, 
            scale(
                np.array(arr),
                vmins[channel],vmaxs[channel],ch*(1-buffer),ch*buffer
            )
        )
    ).transpose().flatten()    
    canvas.create_line(
        *coords,fill=colord[channel]
    )
nfit = 400
def plotfit(henefitpair,irfitpair):    
    if None in henefitpair: return    
    coordsd = {}
    henecalib, etaparams = henefitpair
    henecoords = np.vstack(
        (
            vfits_scaled,
            scale(
                fitter.get_hene_fit(*henecalib)(vfits,*etaparams),
                vmins[HENE],vmaxs[HENE],ch*(1-buffer),ch*buffer
            )
        )
    )    
    coordsd[HENE] = henecoords
    if None not in irfitpair:     
        # (modfreq, *ircalib), f = irfitpair                
        ircalib, f = irfitpair                
        ircoords = np.vstack(
            (
                vfits_scaled,
                scale(
                    fitter.get_ir_fit(*ircalib)(fitter.get_eta(vfits,*etaparams),f),
                    vmins[IR],vmaxs[IR],ch*(1-buffer),ch*buffer
                )
            )
        )
        coordsd[IR] = ircoords
    for channel, coords in coordsd.items():
        canvas.create_line(
            *coords.transpose().flatten(),fill=fitcolord[channel]
        )

def plot_chunk(chunk):    
    if len(chunk) == 1:
        chunk.append([chunk[0][0]+1/2,chunk[0][1]])
    ns, fs = np.array(chunk).transpose()                
    freqcanvas.create_line(
        *np.vstack(
            (
                nscale(ns),
                scale(fs,vmins[FREQ],vmaxs[FREQ],ch*(1-buffer),ch*buffer)
            )
        ).transpose().flatten(),fill = 'green'
    )
def plot_freqs():
    update_limits(FREQ)
    freqcanvas.delete('all')    
    chunk = []
    n = 0
    for freq in freqs:
        if freq is not None:
            chunk.append([n,freq])
        else:
            if chunk:
                plot_chunk(chunk)
                chunk = []
        n += 1
    if chunk:
        plot_chunk(chunk)    

def on_freqs(findexo):
    def _on_freqs(freqsp):
        n = 0
        while freqsp:
            freqs.pop(0)
            freqs.append(freqsp.pop(0))
            n += 1
        fp = freqs[-1]        
        if fp is None:
            flabeltext = 'none'.rjust(16)
        else:
            flabeltext = '{:+.2f} mhz'.format(fp,2).rjust(16)
        freqlabel.config(text=flabeltext)
        plot_freqs()
        findexp = findexo + n        
        window.after(400,start_thread,on_freqs(findexp),tcc.get_frequencies,direction,findexp)
    return _on_freqs
def on_freqs_index(findexp):
    findexo = findexp - history
    start_thread(on_freqs(findexo),tcc.get_frequencies,direction,findexo)

def on_scan(scan):
    if scan is not None:
        index, scandata = scan    
        canvas.delete('all')
        fitpairs = {}
        for channel, channeld in scandata.items():
            plot(channel,channeld[tcs.SCAN])
            fitpairs[channel] = channeld[tcs.FIT]
        plotfit(fitpairs[HENE],fitpairs[IR])
    window.after(50,get_scan)     

errors = {}
results = {}
indexl = [0]
def start_thread(cb,f,*args,**kwargs):    
    index = indexl.pop()    
    indexl.append(index+1)
    def _f():
        try:
            results[index] = f(*args,**kwargs)
        except Exception as e:
            errors[index] = e
    thread = threading.Thread(target=_f)
    thread.start()
    threads.append((cb,thread,index))

threads = []
def loop():
    to_return = []    
    while threads:
        threadtup = threads.pop()
        cb, thread, index = threadtup
        if thread.is_alive():
            to_return.append(threadtup)
            continue
        if index in errors:
            raise errors.pop(index)
        cb(results.pop(index))
    threads.extend(to_return)
    window.after(10,loop)

def get_scan():
    start_thread(
        on_scan,tcc.get_scan,direction,True
    )

def on_vs_full(vs_full):
    global vfits
    vfits = np.array(vs_full)
    global vfits_scaled
    vfits_scaled = vscale(vfits)
    start_thread(on_vs,tcc.get_x,direction,True)

def on_vs(vs):
    vs = np.array(vs)
    vfits = np.linspace(vs.min(),vs.max(),nfit)
    global vs_scaled
    vs_scaled = vscale(vs)
    get_scan()

def on_prop(property):
    def _on_prop(value):
        if property == FREQUENCY:            
            setpointlabel.config(text='{:+.2f} mhz'.format(value,2).rjust(16))
        else:
            pgetters[property].config(
                text={
                    True:'on',False:'off'
                }[value]
            )
        propertyp = properties[(properties.index(property)+1)%len(properties)]
        window.after(
            200,start_thread,on_prop(propertyp),get_prop,propertyp
        )
    return _on_prop

def get_prop(property):
    command = {
        SCANNING:tcc.get_scanning,
        FITTING:tcc.get_fitting,
        LOCKING:tcc.get_locking,
        FREQUENCY:tcc.get_setpoint
    }[property]
    args = [] if property == SCANNING else [direction]
    return command(*args)

start_thread(on_vs_full,tcc.get_x,direction,False)
property = properties[0]
start_thread(on_prop(property),get_prop,property)
start_thread(on_freqs_index,tcc.get_frequencies_index,direction)
window.after(0,loop)
# run
window.mainloop()