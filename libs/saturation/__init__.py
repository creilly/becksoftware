import hitran
from . import bloch
from . import rabi
from . import beam
from . import gamma
from . import doppler

# vvv this function is parallelizable
def get_line_saturation(line,power,diameter,gamma,deltaomega,tau,N,muomega=0.0):
    lined = hitran.lookup_line(line)
    w = lined[hitran.WNUM]
    a = lined[hitran.EIN_COEFF]
    *root, llq, ulq = line
    lj, ls, ll = hitran.parse_lq(llq)
    uj, us, ul = hitran.parse_lq(ulq)    
    m = 0
    n = 0
    prob_sum = 0.0
    # vvv this sum over m is parallelizable
    while True:
        if m > lj:
            break            
        degen = {True:2,False:1}[bool(m)]
        n += degen        
        if m > uj:
            m += 1 
            continue
        omegabar = rabi.rabi_rad_freq(lj,uj,m,w,a,beam.get_intensity(power,diameter))        
        prob = bloch.get_exc_prob(tau,omegabar,gamma,deltaomega,N,muomega) * degen        
        prob_sum += prob
        m += 1
    prob_sum /= n
    return prob_sum

if __name__ == '__main__':
    import numpy as np
    from matplotlib import pyplot as plt
    line = [
        "\u00a06",
        "1",
        "\u00a0\u00a0\u00a0\u00a00\u00a00\u00a00\u00a00\u00a01A1",
        "\u00a0\u00a0\u00a0\u00a00\u00a00\u00a01\u00a00\u00a01F2",
        "\u00a0\u00a0\u00a0\u00a00A1\u00a0\u00a01\u00a0\u00a0\u00a0\u00a0\u00a0",
        "\u00a0\u00a0\u00a0\u00a01A2\u00a0\u00a03\u00a0\u00a0\u00a0\u00a0\u00a0"
    ]
    line = hitran.search_db(6,1,((0,0,0,0),'A1',1),((0,0,1,0),'F2',1),1,6,1)
    power = 1.02 # watts
    diameter = 4.0e-3 # m
    vrmso = 30 # millivolts        
    flow = 0.1
    fhigh = 2.0
    vrmss = vrmso * flow * np.power(fhigh/flow,np.linspace(0,1,30))
    velocity = 1000.0 # m / s    
    tau = beam.get_tau(diameter,velocity)
    deltaomega = doppler.get_deltaomega(velocity)
    N = 1000    
    fs = []
    for vrms in vrmss:
        g = gamma.get_gamma(vrms)
        f = get_line_saturation(line,power,diameter,g,deltaomega,tau,N)
        fs.append(f)
        print(g,f)        
    plt.plot(vrmss,fs)
    plt.xscale('log')
    plt.show()