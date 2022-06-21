import numpy as np
from matplotlib import pyplot as plt
from beckfile import get_fname
from time import time

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

def get_exc_prob(
    tau,omegabar,gamma,sigmaomega,N,muomega=0.0
):
    if omegabar == 0.0:
        return 0.0
    return np.average(
        [
            get_probability(
                tau,omegabar,gamma,deltaomega
            ) for deltaomega in np.random.normal(
                0,sigmaomega,N
            ) + muomega
        ]
    )

if __name__ == '__main__':
    N = 1000
    start = time()
    get_exc_prob(1.0,1.0,1.0,1.0,N)
    stop = time()
    print('delta t for {:d} calculations:'.format(N),stop-start)