#!/bin/bash

module purge
module load intel intel-mkl intel-mpi python

# make named pipes for interprocess communication
p1=pipe1
p2=pipe2

for pipe in $p1 $p2
do
    if [ -e $pipe ]
    then
        rm $pipe
    fi
    mkfifo $pipe
done

# file containing experimental parameters
configfile=$1
# folder containing sanitized data
datafolder=$2
# log file for client process
clientlogfile=$3

# remaining parameters comprise client shell command
shift 3
clientcommand=$@

# start parallel computation job
# run client program (in background) which communicates with parallel computation program
$clientcommand $p1 $p2 $configfile $datafolder &> $clientlogfile &
# run in background with output redirected to log.txt
srun -n $SLURM_NTASKS --partition=$SBATCH_PARTITION python -m fitting.compute $p2 $p1 $configfile $datafolder

# remove the named pipes
rm $p1 $p2

module purge