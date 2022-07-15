#!/bin/sh
python_module=$1
shift 1
slurm_args=${@:1:3}
shift 3
client_args=$@
source _communicate.sh $slurm_args python -m $python_module $client_args