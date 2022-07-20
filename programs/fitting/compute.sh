#!/bin/bash

configfile=$1
datafolder=$2
outputfolder=$3
shift 3
clientcommand=$@

ts=$(date +"%Y%m%d-%H%M%S-%3N")

function get_outputfname() {
    echo "${outputfolder}/${ts}-${1}"
}

configlog=$(get_outputfname config.txt)
cp $configfile $configlog
serveroutputlog=$(get_outputfname server-output.txt)
servererrorlog=$(get_outputfname server-error.txt)
clientoutputlog=$(get_outputfname client-output.txt)
clienterrorlog=$(get_outputfname client-error.txt)

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

module purge
module load intel intel-mkl intel-mpi python
# start parallel computation job
# run client program (in background) which communicates with parallel computation program
$clientcommand -o "${outputfolder}" -t $ts $p1 $p2 "${configfile}" "${datafolder}" 1> "${clientoutputlog}" 2> "${clienterrorlog}" &
clientpid=$!
srun -n $((${SLURM_NTASKS} - 1)) -o "${serveroutputlog}" -e "${servererrorlog}" python -m fitting.compute $p2 $p1 "${configfile}" "${datafolder}"
wait $clientpid
rm $p1 $p2
module purge