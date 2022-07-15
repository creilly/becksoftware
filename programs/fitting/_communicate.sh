#!/bin/bash

configfile=$1

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

sbatch -t $time -n $cores -N $nodes --partition=$partition communicate.sh $@