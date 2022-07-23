from scipy.optimize import minimize
from saturation import communicator

parser = communicator.Parser()
config = parser.get_config()

xo = config.get_factors()
step_size = config.get_step_size()
M = config.get_max_iters()

def sse(factors):
    return client.get_sse(factors)

client = communicator.Client(parser.get_infile(),parser.get_outfile())
res = minimize(
    sse,
    xo,
    method='BFGS',
    options = {
        'disp':True,
        'eps':step_size,
        'maxiter':M
    }
)    
print(res)
client.quit()