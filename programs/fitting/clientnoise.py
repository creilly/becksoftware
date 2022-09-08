from saturation import communicator
import numpy as np
from scipy.optimize import curve_fit
import hitran as ht

N = 16

parser = communicator.Parser()
config = parser.get_config()

factors = config.get_factors()

client = communicator.Client(parser.get_infile(),parser.get_outfile())

ssse = 0.0
ssse2 = 0.0

n = 0
while n < N:
    sse = client.get_sse(factors)
    ssse += sse
    ssse2 += sse**2
    n += 1

print('sse: {:.2e} +- {:.2e}'.format(ssse/N,np.sqrt(ssse2/N-(ssse/N)**2)))

client.quit()