from scipy.optimize import minimize
from saturation import communicator

def minimize(cost_function,xo,step_size,steps):
    step = 0
    x = []
    xmin = []
    nparams = len(xo)
    for n in range(nparams):
        xon = xo[n]
        x.append(xon)
        xmin.append(xon)
    costmin = None
    while step < steps:       
        delta_costs = []
        newmin = False
        for n in range(-1,nparams):
            if n < 0:
                cost_o = cost_function(x)
                if costmin is None or cost_o < costmin:
                    newmin = True
                    costmin = cost_o
                    for m, xm in enumerate(x):
                        xmin[m] = xm                
                continue
            xp = []
            for m in range(nparams):
                xm = x[m]
                if m == n:
                    xm *= 1 + step_size
                xp.append(xm)
            delta_costs.append(cost_function(xp)-cost_o)
        print(
            ' | '.join(
                [
                    '{}: {}'.format(
                        label,data
                    ) for label, data in (
                        ('params',fmt_arr(x,3,10,False)),
                        ('cost',fmt_exp(cost_o,3,10,False)),
                        ('delta costs',fmt_arr(delta_costs,3,10,True)),
                        ('new min',str(newmin))
                    )
                ]
            ),flush=True
        )
        sum_costs = sum(map(abs,delta_costs))
        for n in range(nparams):            
            x[n] *= (1 - delta_costs[n]/sum_costs*step_size)        
        step += 1
    return xmin

def fmt_arr(arr,prec,width,sign):
    return ', '.join(
        [
            fmt_exp(val,prec,width,sign)
            for val in arr
        ]
    )

def fmt_exp(val,prec,width,sign):
    fmtstr = '{{:{}.{:d}e}}'.format(
        '+' if sign else '',
        prec
    )    
    return fmtstr.format(val).rjust(width)

# def _cost_function(params):
#     return np.random.uniform(1,2)

# minimize(_cost_function,[1.0,2.0,3.0],0.1,10)

# exit()

parser = communicator.Parser()
config = parser.get_config()

xo = config.get_factors()
step_size = config.get_step_size()
M = config.get_max_iters()
mask = config.get_mask()

def sse(_factors):
    factors = []
    m = 0
    for n, b in enumerate(mask):
        if b:
            factors.append(_factors[m])
            m += 1
        else:
            factors.append(xo[n])
    return client.get_sse(factors)

client = communicator.Client(parser.get_infile(),parser.get_outfile())
xoo = []
for n, b in enumerate(mask):
    if b:
        xoo.append(xo[n])

xmin = minimize(sse,xoo,step_size,M)
print('optimal parameters:',fmt_arr(xmin,5,11,False))
client.quit()