#!/bin/sh
slurm_args=${@:1:3}
shift 3
client_args=$@
source client.sh fitting.clientplot $slurm_args -f $client_args