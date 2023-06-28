import beckhttpserver as bhs
import os
from datetime import datetime
import pathlib
import json

PORT = 8000

DATAROOTKEY = 'GRAPHERPATH'

if DATAROOTKEY not in os.environ:
    print('error: %s environment variable must be set to desired root folder for data' % DATAROOTKEY)
    exit(10)
    
DATAROOT = os.environ[DATAROOTKEY]

CREATED = '_created'

def check_read_only(f):
    def _f(*args,**kwargs):
        if readonly:
            raise bhs.BeckError(
                ' '.join(
                    [
                        'grapher in read-only mode.',
                        'can not execute command.',
                        'run grapher with --readwrite option set (python -m grapher.graphserver --readwrite).'
                    ]
                )
            )
        return f(*args,**kwargs)
    return _f

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

@check_read_only
def add_folder(folder):
    root = get_day_folder()
    new_folder = root+folder
    _add_folder(new_folder)   
    return new_folder

def get_dir(folder):
    folder_string = format_path_list(folder)
    entries = os.listdir(folder_string)
    dsfiles = []
    folders = []
    mdfiles = []
    for entry in entries:
        fullpath = os.path.join(folder_string,entry)
        if os.path.isfile(fullpath):
            _, ext = os.path.splitext(fullpath)
            if ext == '.tsv':
                dsfiles.append(entry)
            if ext == '.bmd':
                mdfiles.append(entry)
        elif os.path.isdir(fullpath):
            folders.append(entry)
    return sorted(dsfiles), sorted(folders), sorted(mdfiles)

def get_files(folder): return get_dir(folder)[0]
def get_folders(folder): return get_dir(folder)[1]

@check_read_only
def add_dataset(folder,name,fields,metadata):
    _add_folder(folder)
    nfiles = len(get_files(folder))
    fileroot = '{:05d}{}'.format(nfiles,'-{}'.format(name) if name else name)
    dsname = '{}.tsv'.format(fileroot)
    mdname = '{}.bmd'.format(fileroot)
    mdpath = folder + [mdname]
    _metadata = {CREATED:datetime.now().isoformat()}
    if metadata is not None:
        _metadata.update(metadata)
    with open(format_path_list(mdpath),'w') as f:
        f.write(
            json.dumps(
                _metadata,
                sort_keys = True,
                indent = 4
            )
        )            
    dspath = folder + [dsname]
    with open(format_path_list(dspath),'w') as f:
        f.write(
            '# ' + '\t'.join(
                fields
            ) + '\n'            
        )
    return dspath

@check_read_only
def add_data(path,data):
    with open(format_path_list(path),'a') as f:
        f.write(
            '\t'.join(
                map(
                    '{:.10e}'.format,
                    data
                )
            ) + '\n'
        )
    return 0

@check_read_only
def add_data_multiline(path,data):
    with open(format_path_list(path),'a') as f:
        f.write(
            '\n'.join(
                '\t'.join(
                    map(
                        '{:.10e}'.format,
                        row
                    )
                ) for row in data
            ) + '\n'
        )
    return 0

@check_read_only
def update_metadata(path,dmd):
    md = get_metadata(path)
    md.update(dmd)
    with open(format_path_list(path),'w') as f:
        json.dump(
            md,f,
            sort_keys = True,
            indent = 4
        )

def path_status(path):
    return pathlib.Path(format_path_list(path)).stat().st_mtime

def dataset_status(path):
    return path_status(path)

def folder_status(path):
    return path_status(path)

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

def get_metadata(path):
    raw_md = open(format_path_list(path),'r').read()    
    return json.loads(raw_md)

# added 01.03.2022. previous datasets will return None
def get_created(path):
    metadata = get_metadata(path)
    if type(metadata) is dict:
        return metadata.get(CREATED,None)
    else:
        return None

def get_fields(path):
    return open(format_path_list(path),'r').readline().strip()[2:].split('\t')

def format_path_list(path_list):
    path = os.path.join(DATAROOT,*path_list)
    if not bhs.check_path(DATAROOT,path):        
        raise bhs.BeckError('illegal grapher filepath')
    return path

commands = {
    'add-folder':add_folder,
    'dataset-status':dataset_status,
    'add-dataset':add_dataset,
    'add-data':add_data,
    'add-data-multiline':add_data_multiline,
    'get-data':get_data,
    'get-metadata':get_metadata,
    'get-created':get_created,
    'get-fields':get_fields,
    'get-dir':get_dir,
    'get-day-folder':get_day_folder,
    'folder-status':folder_status,
    'update-metadata':update_metadata
}

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='grapher server')
    ap.add_argument('--readonly', action='store_true')
    ap.add_argument('--readwrite',dest='readonly',action='store_false')
    ap.set_defaults(readonly=True)
    readonly = ap.parse_args().readonly
    bhs.run_beck_server(
        PORT,
        os.path.dirname(__file__),
        bhs.create_app(commands),
        _debug=True
    )
