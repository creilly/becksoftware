#!/bin/bash

configfile=$1

source ini-file-parser.sh

process_ini_file $configfile

cmp="computational"

function get_cmp () {
    echo $(get_value $cmp "${1}")
}

cores=$(get_cmp cores)
partition=$(get_cmp partition)
time=$(get_cmp time)

sbatch -t $time -n $cores --partition=$partition communicate.sh $@