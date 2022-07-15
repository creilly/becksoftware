source ini-file-parser.sh

process_ini_file config.ini

cmp="computational"
exp=experimental

function get_cmp() {
    echo $(get_value $cmp "${1}")
}

echo $(get_value $cmp 'cores')

echo $(get_cmp velocity)