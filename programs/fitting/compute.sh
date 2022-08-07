#!/bin/bash

# read config filename from command line args
configfile=$1
# rest of command line args compose the client command
shift 1
clientcommand=$@

# generate timestamp to indentify the computation instance
ts=$(date +"%Y%m%d-%H%M%S-%3N")

# load config file reading library
source config.sh $configfile

# get output data folder from config file
outputfolder=$(get_cmp outputfolder)

# construct folder for computation instance
instancefolder="${outputfolder}/${ts}"

# create folder for computation instance
mkdir -p "${instancefolder}"

# generate
function get_outputfname {
    echo "${instancefolder}/${1}"
}

configlog=$(get_outputfname config.txt)
cp $configfile $configlog
serveroutputlog=$(get_outputfname server-output.txt)
servererrorlog=$(get_outputfname server-error.txt)
clientoutputlog=$(get_outputfname client-output.txt)
clienterrorlog=$(get_outputfname client-error.txt)
clientcommandlog=$(get_outputfname client-command.txt)
touch "${clientcommandlog}"
echo "${clientcommand}" > "${clientcommandlog}"

# make named pipes for interprocess communication
piperoot=/home/reilly/tmp/pipes/pipe
pipeindex=1

function get_pipe {
    if [ -z $1 ]
    then
        local pipeindex=1
    else
        local pipeindex=$1
    fi    
    pipename="${piperoot}$(printf %03d $pipeindex)"    
    if [ -e $pipename ]
    then        
        pipeindex=$((pipeindex + 1))
        get_pipe $pipeindex
    else
        mkfifo $pipename
        echo $pipename
    fi
}

p1=$(get_pipe)
p2=$(get_pipe)

module purge
module load intel intel-mkl intel-mpi python
# start parallel computation job
# run client program (in background) which communicates with parallel computation program
$clientcommand -t $ts -a $p1 -b $p2 -c "${configfile}" 1> "${clientoutputlog}" 2> "${clienterrorlog}" &
clientpid=$!
srun -n $((${SLURM_NTASKS} - 1)) -o "${serveroutputlog}" -e "${servererrorlog}" python -m fitting.compute -a $p2 -b $p1 -c "${configfile}"
wait $clientpid
rm $p1 $p2
module purge