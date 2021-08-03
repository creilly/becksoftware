import http.server
from http import HTTPStatus
import os
from datetime import datetime
import json
import shutil
import mimetypes
import pathlib

PORT = 8000

indexjs = 'index.js'
indexcss = 'index.css'

DATAROOT = r'Z:\Surface\chris\grapher-data'

JSONTYPE = 'application/json'

COMMAND = 'command'
PARAMETERS = 'parameters'
LENGTHTOKEN = '_length'

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
    return files, folders

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

commands = {
    'add-folder':add_folder,
    'dataset-status':dataset_status,
    'add-dataset':add_dataset,
    'add-data':add_data,
    'get-data':get_data,
    'get-fields':get_fields,
    'get-dir':get_dir,
    'get-day-folder':get_day_folder
}

def format_path_list(path_list):
    return format_relative_path(
        os.path.join(DATAROOT,*path_list)
    )

def format_relative_path(relative_path):
    return os.path.join(root_folder,relative_path)

root_folder = os.path.dirname(__file__)

class GraphRequestHandler(http.server.BaseHTTPRequestHandler):
        
    def do_GET(self):
        path = self.path.split('/',1)[1]
        if not path:
            path = 'index.html'
        path = format_relative_path(path)
        if os.path.isfile(path):
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type',mimetypes.guess_type(path)[0])
            self.end_headers()
            shutil.copyfileobj(open(path,'rb'),self.wfile)
            return
        else:
            self.send_error(http.HTTPStatus.NOT_FOUND)
            return

    def do_POST(self):
        # print('headers:')
        # print(self.headers)
        rawdata = self.rfile.read(
            int(
                self.headers['content-length']
            )
        ).decode('utf-8')
        data = json.loads(rawdata)
        command = data[COMMAND]
        parameters = data[PARAMETERS]
        response = commands[command](**parameters)
        # uncomment to sniff traffic
        # print(command,parameters,data)
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type',JSONTYPE)
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

with http.server.ThreadingHTTPServer(('', PORT), GraphRequestHandler) as httpd:
    print('serving at port', PORT)
    httpd.serve_forever()
