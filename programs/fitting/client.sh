#!/bin/sh
# args:
#   1:  name of python module (omit .py extension). must be in PYTHONPATH    
#   2:  config file
#   3:  data folder
#   4:  output folder
#   *:  extra args to be passed to client program
python_module=$1
shift 1
slurm_args=${@:1:1}
shift 1
client_args=$@
source communicate.sh $slurm_args python -m $python_module $client_args