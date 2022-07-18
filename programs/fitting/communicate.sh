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
sbatch -n $cores -N $nodes -p $partition -t $time compute.sh $configfile $datafolder $outputfolder $clientcommand