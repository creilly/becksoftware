import tkinter as tk, tc.tcclient as tcc, numpy as np, threading, time
from tc.scanner import Scanner as S
from tc import tcserver as tcs, fitter
from argparse import ArgumentParser as AP

ap = AP(description='transfer cavity gui client')
ap.add_argument('--direction','-d',choices=(S.UP,S.DOWN))

DEFAULT_WIDTH = 500
DEFAULT_HEIGHT = 700
BUFFER = 0.05

direction = ap.parse_args().direction

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
window.geometry(f'{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}')
window.title('transfer cavity')

# Configure grid weights for responsiveness
window.columnconfigure(0, weight=1, minsize=5)  # Expand left spacer to push controls right
window.columnconfigure(1, weight=0)  # Keep control columns tight
window.columnconfigure(2, weight=0)
window.columnconfigure(3, weight=0)
window.columnconfigure(4, weight=0, minsize=5)
window.columnconfigure(5, weight=0, minsize=5)
window.columnconfigure(6, weight=0, minsize=5)

# canvas 
canvas = tk.Canvas(window, bg='white')
row = 0
canvas.grid(row=row, column=0, columnspan=7, padx=3, pady=3, sticky='nsew')
window.rowconfigure(row, weight=1)
row += 1

fmin = -10
fmax = +10
history = 1500
freqs = [None] * history

vsetters = {}

def create_plot_controls(channel, units):
    column = 1    
    for vlimit in (VMIN,VMAX):
        tk.Label(
            window,
            text='{} {} ({})'.format(
                {HENE:'hene',IR:laser,FREQ:'freq'}[channel],{
                    VMIN:'min', VMAX:'max'
                }[vlimit],units
            )
        ).grid(row=row,column=column,sticky='E')
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
            window,textvariable=stringvar,width=8         
        ).grid(row=row,column=column,sticky='E')      
        column += 1  
for channel in (HENE,IR):
    create_plot_controls(channel,'v')
    row += 1

pgetters = {}
for property in (SCANNING,FITTING,LOCKING):    
    tk.Label(window,text=property).grid(row=row,column=1,sticky='E')    
    pgetter = tk.Label(window,text='none')
    pgetter.grid(row=row,column=2,sticky='E')    
    pgetters[property] = pgetter
    intvar = tk.IntVar()
    psetter = tk.Checkbutton(window,variable=intvar)
    psetter.grid(row=row,column=3,sticky='E')        
    def get_command(intvar,function,args):
        def command():
            start_thread(
                lambda *_: None,
                function,
                *args,bool(intvar.get())
            )
        return command
    tk.Button(
        window,text='set',width=6,command=get_command(
            intvar, {
                SCANNING:tcc.set_scanning,
                FITTING:tcc.set_fitting,
                LOCKING:tcc.set_locking
            }[property], [] if property == SCANNING else [direction]
        )
    ).grid(row=row,column=4,sticky='E',padx=2)
    row += 1

# frequency controls frame: don't expand to full width so internal spacing stays tight
# frequency frame occupies columns 1-3; leave column 4 for the main 'set' button
freqframe = tk.Frame(window)
freqframe.grid(row=row, column=1, columnspan=3, sticky='E', pady=4)
# compact fixed columns inside the frame
for _i in range(6):
    freqframe.columnconfigure(_i, weight=0)
row += 1

frow = 0
# Use pack inside the freqframe so items stay tightly grouped and don't get stretched
# when the main grid columns resize. Use minimal padding and right-anchored numeric labels.
tk.Label(freqframe, text='freq', width=4).pack(side='left', padx=(0,1))
tk.Label(freqframe, text='meas:', width=4).pack(side='left', padx=(0,1))
freqlabel = tk.Label(freqframe, text='none', width=12, font=('courier',10), anchor='e', justify='right')
freqlabel.pack(side='left', padx=(0,2))
tk.Label(freqframe, text='sp:', width=3).pack(side='left', padx=(0,1))
setpointlabel = tk.Label(freqframe, text='none', width=12, font=('courier',10), anchor='e', justify='right')
setpointlabel.pack(side='left', padx=(0,2))
setpointvar = tk.StringVar(freqframe, value='none')
setpointentry = tk.Entry(freqframe, textvariable=setpointvar, width=12)
setpointentry.pack(side='left', padx=(0,2))

def setpoint_cb():
    raw_setpoint = setpointvar.get()
    try:
        setpoint = float(raw_setpoint)
    except ValueError:
        print('error parsing setpoint: "{}"'.format(raw_setpoint))
        return
    start_thread(lambda *_: None, tcc.set_setpoint, direction, setpoint, wait=False)

# Place the 'set' button in the main grid so it lines up with other 'set' buttons
# freqframe was placed at `row`, then row was incremented; place the button on the
# same logical row as the freqframe (row - 1)
tk.Button(window, text='set', command=setpoint_cb, width=6).grid(row=row-1, column=4, sticky='E', padx=2)

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
    row=row,column=1,sticky='E'
)

row += 1

create_plot_controls(FREQ,'mhz')
row += 1

# canvas 
freqcanvas = tk.Canvas(window, bg='white')
freqcanvas.grid(row=row, column=0, columnspan=7, padx=3, pady=3, sticky='nsew')
window.rowconfigure(row, weight=1)
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
    cw = canvas.winfo_width()
    if cw <= 1:
        cw = 400  # fallback default width
    return scale(v, vmin, vmax, cw*BUFFER, cw*(1-BUFFER))

def Vscale(V):
    ch = canvas.winfo_height()
    return scale(V, Vmin, Vmax, ch*(1-BUFFER), ch*BUFFER)

def nscale(n):
    cw = freqcanvas.winfo_width()
    if cw <= 1:
        cw = 400  # fallback default width
    return scale(n, 0, history, cw*BUFFER, cw*(1-BUFFER))

def fscale(f):
    ch = freqcanvas.winfo_height()
    return scale(f, fmin, fmax, ch*(1-BUFFER), ch*BUFFER)

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
    ch = canvas.winfo_height()
    cw = canvas.winfo_width()
    if cw <= 1:
        cw = 400
    # Recalculate vs_scaled based on current canvas width
    vs_scaled_current = scale(vs_scaled_raw, vmin, vmax, cw*BUFFER, cw*(1-BUFFER))
    coords = np.vstack(
        (
            vs_scaled_current, 
            scale(
                np.array(arr),
                vmins[channel],vmaxs[channel],ch*(1-BUFFER),ch*BUFFER
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
    ch = canvas.winfo_height()
    cw = canvas.winfo_width()
    if cw <= 1:
        cw = 400
    # Recalculate vfits_scaled based on current canvas width
    vfits_scaled_current = scale(vfits_scaled_raw, vmin, vmax, cw*BUFFER, cw*(1-BUFFER))
    henecalib, etaparams = henefitpair
    henecoords = np.vstack(
        (
            vfits_scaled_current,
            scale(
                fitter.get_hene_fit(*henecalib)(vfits,*etaparams),
                vmins[HENE],vmaxs[HENE],ch*(1-BUFFER),ch*BUFFER
            )
        )
    )    
    coordsd[HENE] = henecoords
    if None not in irfitpair:     
        ircalib, f = irfitpair                
        ircoords = np.vstack(
            (
                vfits_scaled_current,
                scale(
                    fitter.get_ir_fit(*ircalib)(fitter.get_eta(vfits,*etaparams),f),
                    vmins[IR],vmaxs[IR],ch*(1-BUFFER),ch*BUFFER
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
    ch = freqcanvas.winfo_height()
    freqcanvas.create_line(
        *np.vstack(
            (
                nscale(ns),
                scale(fs,vmins[FREQ],vmaxs[FREQ],ch*(1-BUFFER),ch*BUFFER)
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
            flabeltext = 'none'
        else:
            flabeltext = '{:+.2f} mhz'.format(fp)
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
    global vfits_scaled_raw
    vfits_scaled_raw = vfits
    start_thread(on_vs,tcc.get_x,direction,True)

def on_vs(vs):
    vs = np.array(vs)
    vfits = np.linspace(vs.min(),vs.max(),nfit)
    global vs_scaled_raw
    vs_scaled_raw = vs
    get_scan()

def on_prop(property):
    def _on_prop(value):
        if property == FREQUENCY:            
            setpointlabel.config(text='{:+.2f} mhz'.format(value))
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