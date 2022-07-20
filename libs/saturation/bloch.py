import numpy as np

np.random.seed()

def get_probability(
    tau,omegabar,gamma,deltaomega
):
    if omegabar == 0.0:
        return 0.0
    M = [
        [
            -gamma,     -deltaomega,        0
        ],[
            deltaomega, -gamma,             omegabar
        ],[
            0,          -omegabar,          0
        ]    
    ]

    w, S = np.linalg.eig(M)

    Sinv = np.linalg.inv(S)        

    sigmaz = sum(
        -np.exp(w[j]*tau)*S[2][j]*Sinv[j][2]
        for j in range(3)
    )

    prob = 1/2*(1 + sigmaz)

    return np.abs(prob)

def get_deltaomegas_normal(muomega,sigmaomega,N):
    return np.random.normal(
        muomega,sigmaomega,N
    )

R = 2.0
r = 1.0
sigmageometric = 0.912591
def get_deltaomegas_geometric(muomega,sigmaomega,N):
    rs = np.random.uniform(0.0,r,N)
    thetars = np.random.uniform(0.0,2.0 * np.pi,N)

    Rs = np.random.uniform(0.0,R,N)
    thetaRs = np.random.uniform(0.0,2.0 * np.pi,N)

    return muomega + sigmaomega / sigmageometric * (
        Rs * np.sin(thetaRs) - rs * np.sin(thetars)
    )

rtpi = np.sqrt(np.pi)
def get_taus(tau,N):
    taup = tau/rtpi
    return 2 * np.sqrt(taup**2 - np.random.uniform(0,taup,N)**2)

# vvv this average over N is parallelizable
def get_exc_prob(
    tau,omegabar,gamma,sigmaomega,N,muomega=0.0
):
    if omegabar == 0.0:
        return 0.0
    return np.average(
        [
            get_probability(
                tau_circ,omegabar,gamma,deltaomega
            ) for deltaomega, tau_circ in zip(
                get_deltaomegas_geometric(
                    muomega,sigmaomega,N
                ),
                get_taus(tau,N)
            )
        ]
    )

if __name__ == '__main__':
    M = 100000
    from matplotlib import pyplot as plt
    from time import time
    n_samples = get_deltaomegas_normal(0,1,M)
    sigma_n = np.std(n_samples)
    print('normal stddev:',sigma_n)
    plt.hist(
        n_samples,
        color=(0.0,0.0,1.0,0.5),
        bins=50,
        label = 'normal'
    )
    g_samples = get_deltaomegas_geometric(0,1,M)
    
    sigma_g = np.std(g_samples)
    print('geometric stddev:',sigma_g)
    print('factor:',1/sigma_g)
    plt.hist(
        g_samples,
        color=(0.0,1.0,0.0,0.5),
        bins=50,
        label = 'geometric'
    )
    plt.legend()
    plt.show()
    N = 1000
    start = time()
    get_exc_prob(1.0,1.0,1.0,1.0,N)
    stop = time()
    print('delta t for {:d} calculations:'.format(N),stop-start)