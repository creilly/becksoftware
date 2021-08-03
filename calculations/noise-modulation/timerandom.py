from timeit import default_timer as clock
import numpy as np

N = 100000
np.random.seed()

start = clock()
np.random.normal(0,1,N)
print('normal:',clock()-start)

start = clock()
np.random.uniform(0,1,N)
print('uniform:',clock()-start)
