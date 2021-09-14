import beckhttpserver as bhs
import os
from datetime import datetime
import pathlib

PORT = 8000

DATAROOTKEY = 'GRAPHERPATH'

if DATAROOTKEY not in os.environ:
    print('error: %s environment variable must be set to desired root folder for data' % DATAROOTKEY)
    exit(10)
    
DATAROOT = os.environ[DATAROOTKEY]

def get_day_folder():
    now = datetime.now()
    return [
        s.format(now) for s in (
            '{:%Y}','{:%m}','{:%d}'
        )
    ]

def _add_folder(folder):
    folder_string = format_path_list(folder)
    if not os.path.exists(folder_string):
        os.makedirs(folder_string)
    
def add_folder(folder):
    root = get_day_folder()
    new_folder = root+folder
    _add_folder(new_folder)   
    return new_folder

def get_dir(folder):
    folder_string = format_path_list(folder)
    entries = os.listdir(folder_string)
    files = []
    folders = []
    for entry in entries:
        fullpath = os.path.join(folder_string,entry)
        if os.path.isfile(fullpath):
            files.append(entry)
        elif os.path.isdir(fullpath):
            folders.append(entry)
    return sorted(files), sorted(folders)

def get_files(folder): return get_dir(folder)[0]
def get_folders(folder): return get_dir(folder)[1]

def add_dataset(folder,name,fields):
    _add_folder(folder)
    nfiles = len(get_files(folder))
    filename = '{:05d}-{}.tsv'.format(nfiles,name)
    path = folder + [filename]
    with open(format_path_list(path),'w') as f:
        f.write(
            '# ' + '\t'.join(
                fields
            ) + '\n'            
        )
    return path

def add_data(path,data):
    with open(format_path_list(path),'a') as f:
        f.write(
            '\t'.join(
                map(
                    '{:e}'.format,
                    data
                )
            ) + '\n'
        )
    return 0

def add_data_multiline(path,data):
    with open(format_path_list(path),'a') as f:
        f.write(
            '\n'.join(
                '\t'.join(
                    map(
                        '{:e}'.format,
                        row
                    )
                ) for row in data
            ) + '\n'
        )
    return 0

def dataset_status(path):
    return pathlib.Path(format_path_list(path)).stat().st_mtime

def get_data(path):
    return list(
        zip(
            *[
                [
                    float(d) for d in line.split('\t')
                ] for line in open(format_path_list(path),'r').read().strip().split('\n')[1:]
            ]
        )
    )

def get_fields(path):
    return open(format_path_list(path),'r').readline().strip()[2:].split('\t')

def format_path_list(path_list):
    return os.path.join(DATAROOT,*path_list)

commands = {
    'add-folder':add_folder,
    'dataset-status':dataset_status,
    'add-dataset':add_dataset,
    'add-data':add_data,
    'add-data-multiline':add_data_multiline,
    'get-data':get_data,
    'get-fields':get_fields,
    'get-dir':get_dir,
    'get-day-folder':get_day_folder
}

bhs.run_beck_server(
    PORT,
    os.path.dirname(__file__),
    bhs.create_app(commands),
    _debug=False
)
