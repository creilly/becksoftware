from mpi4py import MPI
import numpy as np
from time import perf_counter
from saturation import rabi, gamma, doppler, beam, bloch, sanitize
from scipy.optimize import minimize
from saturation import communicator
import configparser

debug = False

# get command line arguments
# argument list:
#   -a, --infile        : input filename for inter-process communcation
#   -b, --outfile       : output filename for ipc
#   -c, --configfile    : filename of computation and experimental params
parser = communicator.Parser()

# config file storing
config = parser.get_config()

# computational parameters
# number of monte carlo samples per quantum state probability calculation (qspc)
N = config.get_N()
# folder containing sanitized data and metadata
datafolder = config.get_datafolder()

# experimental parameters
beam_diameter = config.get_diameter() # meters
noise_amplitude = config.get_vrms() # millivolts rms
velocity = config.get_velocity() # meters per second

# model parameter computation
tau = beam.get_tau(beam_diameter,velocity) * 1e6 # us
sigmaomega = doppler.get_deltaomega(velocity) * 1e-6 # rads / us

nfactors = 4
# stores current correction factors
factors = np.empty(nfactors)

# degeneracy multiplier matrix initialization
jmax = 20
degens = np.array([2 if m else 1 for m in range(jmax + 1)])

# matrix prototypes
M_deltaomega = [
    [   0,     -1,    0   ],
    [  +1,      0,    0   ],
    [   0,      0,    0   ]
]

M_gamma = [
    [  -1,      0,    0   ],
    [   0,     -1,    0   ],
    [   0,      0,    0   ]
]

M_omegabar = [
    [   0,      0,    0   ],
    [   0,      0,   +1   ],
    [   0,     -1,    0   ]
]

M_deltaomega, M_gamma, M_omegabar = map(np.array,(M_deltaomega,M_gamma,M_omegabar))

# MPI initialization
comm = MPI.COMM_WORLD
size = comm.Get_size() # number of cores
rank = comm.Get_rank() # core id
masterrank = 0 # size - 1 # core id of master core

md = sanitize.load_metadata(datafolder) # dataset metadata
cgcd = sanitize.load_cgc(datafolder) # pre-computed clebsch gordan coefficients

# total number of quantum states to compute
def get_total_length():
    total_length = 0
    for lined in md:        
        total_length += lined['length'] * len(lined['cgcs'])
    return total_length

END = -1 # marks end of job division transmission
sendrequests = [] # stores asynchronous send requests
recvrequests = [] # stores asynchronous recv requests
data = [] # stores unchanging model data

MEASURED, COMPUTED = 0, 1
arrays = [] # stores job division information
dataarrays = {} # stores computed and measured scientific data
indexbuffer = np.empty(3,dtype=np.int64) # stores job division tranmission data

# synchronous buffer send (thin wrapper)
def send(buffer,dest):
    comm.Send(buffer,dest)
# asynchronous buffer send 
# sendrequests needed to prevent garbage collection of asychronous requests
def isend(buffer,dest):
    sendrequests.append(comm.Isend(buffer,dest))
# synchronous (blocking) recv
def recv(buffer,source):
    comm.Recv(buffer,source)
# asynchronous (nonblocking) recv
def irecv(buffer,source,jobindex):    
    recvrequests[jobindex][source] = comm.Irecv(buffer,source)
# clear send request list
def clear_sends():
    while sendrequests:
        sendrequests.pop(0).Wait()    
# complete all pending recvs
def wait_recvs():
    for jobd in recvrequests:
        for request in jobd.values():
            request.Wait()    

# read data from disk
# compute unchanging model data
# transmit measured data to masterrank
def get_data():
    total_length = get_total_length() # total num of q state prob calcs (qspcs)
    chunk = total_length // size # total num of qspcs for each rank
    rankmarker = 0 # num of qspcs for current chunk 
    _rank = 0 # rank of current chunk
    # loop through datasets, determine job load 
    for lineindex, lined in enumerate(md):        
        # clebsch gordan coefficients
        # first element must be m=0
        cgcs = lined['cgcs']
        n_m = len(cgcs) # qspcs per point on curve (fc or fs)        
        linelength = lined['lengths'] # num data points in curve
        linemarker = 0 # current position along curve
        while True:
            linetail = linelength - linemarker # points remaining in curve
            ranktail = chunk - rankmarker # qspcs left in chunk                
            # if qspcs left in curve is greater than qspcs left in chunk:
            #   advance modemarker to fill chunk (rounding up)
            # else:
            #   advance modemarker to end of curve
            tail = (
                ranktail // n_m + (1 if ranktail % n_m else 0)
            ) if linetail * n_m > ranktail else linetail
            # if current rank is equal to core id
            if rank == _rank:  
                # pull current segment of curve data from disk                  
                # deltaomegas: rads / us
                # omegabars: rads / us
                # gammas: rads / us
                # zs (detector signals): normed
                # shape (of each) : (tail,)
                deltaomegas, omegabars, gammas, zs = sanitize.load_data(
                    lineindex,datafolder
                )[linemarker:linemarker+tail].transpose()
                # compute rabi frequencies (omegabar) for each qspc of curve segment
                # shape : (n_m,tail)                    
                m_omegabars = np.outer(cgcs,omegabars) # rads / us (n_m, n_points)
                # scale omegabar matrix term by all omegabars for each qspc of curve segment
                # shape : (n_m,tail,3,3)
                M_omegabars = np.einsum('ij,kl->ijkl',m_omegabars,M_omegabar)
                # scale gamma matrix term by all gammas for each 
                # shape : (tail,3,3)
                M_gammas = np.einsum('i,jk->ijk',gammas,M_gamma)
                # save deltaomega (frequency detuning) and omegabar data for this curve segment to local memory
                data.append(
                    (
                        deltaomegas,M_omegabars,M_gammas
                    )
                )
                # send curve segment metadata to masterrank
                start = linemarker
                stop = linemarker + tail
                isend(np.array((lineindex,start,stop),dtype=np.int64),masterrank)
                # send curve segment measured data to masterrank
                isend(np.ascontiguousarray(zs),masterrank)
                if debug:
                    print(
                        '*','\t\t'.join(
                            '{}: {:d}'.format(label,num) for label, num in (
                                ('rank',_rank),
                                ('line',lineindex),                                
                                ('start',start),
                                ('stop',stop)
                            )
                        ),flush=True                
                    )  
            # advance chunk marker                  
            rankmarker += tail * n_m
            # if current chunk is larger than chunk size
            if chunk - rankmarker <  n_m:
                # if current rank is core id
                if rank == _rank:
                    # signal end of job division info transmission
                    isend(np.array([END]*3),masterrank)
                # reset chunk marker
                rankmarker = 0
                # increment rank marker
                _rank += 1             
                # if previous rank was core id       
                if rank < _rank:
                    # exit
                    return
            # advance curve marker
            linemarker += tail
            # if curve marker is at end of curve
            if linemarker == linelength:
                # go to next curve
                break   
    # last rank will typically not have full chunk of qspcs
    # signal end of job division info transmission for this edge case
    # (that's why we make it the masterrank)
    isend(np.array([END]*3),masterrank)

# organize masterrank data arrays
# collect transmitted job division information
def finish_get_data():
    if rank == masterrank:  
        # loop through lines
        for lineindex, lined in enumerate(md):            
            # pull curve length from metadata
            linelength = lined['length']
            # allocate memory for measured and computed data
            dataarrays[lineindex] = {
                zmode:arr for zmode, arr in zip(
                    (MEASURED,COMPUTED),
                    np.empty(2*linelength).reshape((2,linelength))
                )
            }            
        # loop through cores
        for _rank in range(size):
            # create job division list for current core
            rankarrays = []            
            arrays.append(rankarrays)
            # loop through each curve segment for current core
            jobindex = 0  
            while True:
                # get curve segment metadata
                recv(indexbuffer,_rank)
                lineindex, start, stop = indexbuffer
                if debug:
                    print(
                        '\t\t'.join(
                            '{}: {:d}'.format(label,num) for label, num in (
                                ('rank',_rank),
                                ('line',lineindex),
                                ('start',start),
                                ('stop',stop)
                            )
                        ),flush=True                
                    )
                # if end of transmission signalled, move on to next core
                if lineindex == END:
                    break            
                # if current core has more curve segments than all previous cores,
                # append a dict to recv request list for this curve segment index
                if jobindex == len(recvrequests):
                    jobd = {}
                    recvrequests.append(jobd)
                # get allocated data for the full curve of this curve segment
                datad = dataarrays[lineindex]
                # initiate data transfer to fill the appropriate segment of the 
                # full measured curve buffer with measured data transmitted by current core                
                irecv(datad[MEASURED][start:stop],_rank,jobindex)
                # put pointer to appropriate segment of full computed curve buffer
                # at appropriate location of job division progression
                rankarrays.append(datad[COMPUTED][start:stop])
                jobindex += 1
        # finish data transfers
        wait_recvs()
    # all cores clear their send requests        
    clear_sends()    

def init():
    get_data()
    finish_get_data()

# compute simulated curves for all curves
def get_outdata():
    # start performance monitor clock
    start = perf_counter()
    # adjust model parameters with fudge factors
    power_factor, gamma_factor, velocity_factor, diameter_factor = factors    

    # model parameter computation    
    taup = diameter_factor / velocity_factor * tau # us
    sigmaomegap = velocity_factor * sigmaomega # rads / us    
    
    # initiate data transfers of updated computed curves
    if rank == masterrank:        
        for _rank, rankarrays in enumerate(arrays):
            for jobindex, arr in enumerate(rankarrays):
                irecv(arr,_rank,jobindex)
    # loop over curve segments of this core
    for deltaomegas, M_omegabars, M_gammas in data:
        # n_mu : quantum states per curve point
        # n_points : num points in curve segment        
        n_m, n_points, *_ = M_omegabars.shape
        # compute N random frequency detunings (rfd) for each qspc
        # shape : (N,n_mu,n_points)
        d_deltaomegas = bloch.get_deltaomegas_geometric(
            0.0,sigmaomegap,N*n_m*n_points
        ).reshape((N,n_m,n_points))
        # offset rfd by known frequency detuning for each curve point
        # shape : (N,n_mu,n_points)
        deltaomegasp = d_deltaomegas + deltaomegas
        # scale deltaomega matrix term by each offset rfd
        # shape : (N,n_mu,n_points,3,3)
        M_deltaomegasp = np.einsum('ijk,lm->ijklm',deltaomegasp,M_deltaomega)
        # assemble dynamical matrix for each rfd
        # shape : (N,n_mu,n_points,3,3)
        Ms = (gamma_factor * M_gammas + np.sqrt(power_factor) / diameter_factor * M_omegabars) + M_deltaomegasp
        # compute eigenvalues (lambdas) and eigenvectors (Ss) for each rfd
        # shape (lambdas) : (N,n_mu,n_points,3)
        # shape (Ss) : (N,n_mu,n_points,3,3)
        lambdas, Ss = np.linalg.eig(Ms)
        # compute inverse of eigenvector matrix for each rfd
        # shape : (N,n_mu,n_points,3,3)
        Sinvs = np.linalg.inv(Ss)        
        # compute random transit time (rtt) for each rfd
        # shape : (N,n_mu,n_points)
        tausp = bloch.get_taus(taup,N*n_m*n_points).reshape((N,n_m,n_points))
        # for each rtt:
        #   take product with each associated eigenvalue
        #   exponentiate
        # shape : (N,n_mu,n_points,3)
        exponents = np.exp(np.einsum('ijk,ijkl->ijkl',tausp,lambdas))
        # take last row of each eigenvector matrix
        # shape : (N,n_mu,n_points,3)
        Szs = Ss[:,:,:,2,:]
        # take last col of each inverse eigenvector matrix
        # shape : (N,n_mu,n_points,3)
        Sinvzs = Sinvs[:,:,:,:,2]        
        #   1. for each rfd
        #       i. take product of:
        #           a) eigenvector matrix row
        #           b) inverse eigenvector matrix col
        #           c) associated eigenvalues
        #           [a), b), c) are all length 3 arrays]
        #       ii. sum the products obtained in step i
        #   2. for each qspc
        #       i.  average sum obtained in 1.ii over random samples
        #       ii. scale and shift averages obtained step i
        # shape : (n_mu,n_points)
        probs = 0.5 + 0.5 * np.real(
            (
                -Szs*Sinvzs*exponents
            ).sum(3)
        ).sum(0) / N
        # get degeneracy factors for this line
        # shape : (n_mu,)
        modedegens = degens[:n_m]        
        #   1. scale probabilities for each qspc by appropriate degeneracy factor, 
        #   2. for each curve point, sum over quantum states
        #   3. divide probability of each curve point by sum of degeneracy factors
        # shape : (n_points,)
        probs = np.einsum('ij,i->j',probs,modedegens) / (2*n_m - 1)
        # send computed data to masterrank
        isend(probs,masterrank)    
    if rank == masterrank:
        # collect computed data
        wait_recvs()
        # intialitize sum squared error
        sse = 0.
        # loop over curves
        for lined in dataarrays.values():
            # get measured curve data
            measured = lined[MEASURED]
            # get freshly computed curve data
            computed = lined[COMPUTED]
            # normalize computed data 
            normalized = computed / computed.sum()
            # compute sum squared error, add to running total                
            sse += ((measured - normalized)**2).sum()
    else:
        sse = None
    # wait for indication of successful send    
    clear_sends()    
    # stop performance timer
    stop = perf_counter()
    if rank == masterrank:
        # write step info to log
        print(
            'iter time:','{:.3f}'.format(stop-start),'s',
            '|',
            'factors:',', '.join('{:.5f}'.format(factor) for factor in factors),
            '|',
            'sse:','{:.4e}'.format(sse),
            flush=True        
        )
    return sse

def main():
    # load input data for this core
    init()
    if rank == masterrank:
        # get interprocess communication handles from command line arguments        
        # initialize communication with client process                
        server = communicator.Server(parser.get_infile(),parser.get_outfile())
        while True:
            # get next command            
            command = server.get_int()             
            if command == communicator.QUIT:
                # fill factors with quitting signal to other cores
                _factors = [-1]*nfactors
            else:
                # get next set of correction factors
                _factors = server.get_factors()                
            # load requested factors into memory
            factors[:] = _factors
            # notify the other cores of factor change
            for _rank in range(size):
                # no need to notify myself
                if _rank == masterrank:
                    continue
                send(factors,_rank)
            # negative factors indicates program termination
            # (maybe not the cleanest method)
            if factors[0] < 0:
                break
            # compute sum squared error
            sse = get_outdata()            
            if command == communicator.SSE:
                # send sse to client
                server.send_sse(sse)
            if command == communicator.DATA:                
                # communicate number of lines
                server.send_int(len(dataarrays))                
                # loop over curves
                for lineindex, lined in dataarrays.items():                    
                    # communicate current line index
                    server.send_int(lineindex)                    
                    # get freshly computed curve data
                    arr = lined[COMPUTED]
                    # communicate length of curve
                    server.send_int(len(arr))                        
                    # send array data
                    server.send_doubles(arr)
    else:        
        while True:
            # get new factors from masterrank
            recv(factors,masterrank)
            # check for termination condition
            if factors[0] < 0:
                break        
            # compute and transfer this core's contribution to model computation
            get_outdata()

if __name__ == '__main__':    
    main()