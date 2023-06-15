from . import InstructionClient, AsyncInstructionClient, get_diode_temperature_ready, get_wide_scan, A, B
import base64
from matplotlib import pyplot as plt
import time

ic = InstructionClient()

response = ic.play_melody()

# ic = InstructionClient()
# for i in range(10):
#     starttime = time.time()
#     print(ic.get_output(A))
#     stoptime = time.time()
#     print('time',stoptime-starttime)

# aic = AsyncInstructionClient()
# ar1 = aic.set_output(A,ic.get_output(A))
# ar2 = aic.set_output(A,ic.get_output(A))
# N = 10
# oa = ic.get_output(A)
# ars = []
# for n in range(N):
#     ars.append(aic.set_output(A,oa))
# m = 0
# starttime = time.time()
# while True:
#     fs = []
#     print('{: 7d} us'.format(int(1e6*(time.time()-starttime))),m,n,f,r)
#     for n, ar in enumerate(ars):
#         f,r = ar.read()
#         fs.append(f)        
#     if all(fs):
#         break
#     m += 1



    
