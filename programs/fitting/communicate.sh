#!/bin/bash
# args:
#   1: config file
#   2: data folder
#   3: output folder
#   4: client command

# file containing experimental parameters
configfile=$1
# folder containing sanitized data
datafolder=$2
# folder for program outputs
outputfolder=$3
# remaining parameters comprise client shell command
shift 3
clientcommand=$@

mkdir -p "$outputfolder"

source ini-file-parser.sh

process_ini_file $configfile

cmp="computational"

function get_cmp () {
    echo $(get_value $cmp "${1}")
}

cores=$(get_cmp cores)
corespernode=28
nodes=$(((cores-1)/corespernode+1))
partition=$(get_cmp partition)
time=$(get_cmp time)

ts=$(date +"%Y%m%d-%H%M%S-%3N")
configlog="${outputfolder}/${ts}-config.txt"
cp $configfile $configlog
serverlog="${outputfolder}/${ts}-server.txt"
clientlog="${outputfolder}/${ts}-client.txt"

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

# start parallel computation job
# run client program (in background) which communicates with parallel computation program
$clientcommand $p1 $p2 $configfile $datafolder $outputfolder $ts &> $clientlog &
clientpid=$!
srun -n $SLURM_NTASKS --partition=$SBATCH_PARTITION python -m fitting.compute $p2 $p1 $configfile $datafolder 2>&1 | tee $serverlog
wait $clientpid
# remove the named pipes
rm $p1 $p2

module purge