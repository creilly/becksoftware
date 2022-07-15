from scipy.optimize import minimize
from saturation import communicator

parser = communicator.get_parser()

parser.add_argument('-f','--factors',nargs=4,type=float)

args = parser.parse_args()

xo = args.factors

client = communicator.Client(*communicator.get_pipes(args))

cp = communicator.get_config(args)

step_size = cp.getfloat('computational','step size')
M = cp.getint('computational','M')

def sse(factors):
    return client.get_sse(factors)

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