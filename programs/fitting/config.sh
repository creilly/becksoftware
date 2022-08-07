#!/bin/bash

source ini-file-parser.sh

configfile=$1

process_ini_file $configfile

cmp=computational

function get_cmp() {
    echo $(get_value $cmp "${1}")
}