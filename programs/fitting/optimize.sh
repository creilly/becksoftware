#!/bin/sh
slurm_args=${@:1:1}
shift 1
client_args=$@
source client.sh fitting.clientoptimize $slurm_args $client_args