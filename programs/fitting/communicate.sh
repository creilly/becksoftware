#!/bin/bash
# args:
#   1       : config file
#   2 ... N : client command

# file containing experimental parameters and computational
configfile=$1
# remaining parameters comprise client shell command
shift 1
clientcommand=$@

# load config file
source config.sh $configfile

cores=$(get_cmp cores)
corespernode=28
nodes=$(((cores-1)/corespernode+1))
partition=$(get_cmp partition)
time=$(get_cmp time)

sbatch -o /dev/null -n $cores -N $nodes -p $partition -t $time compute.sh $configfile $clientcommand