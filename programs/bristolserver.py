import http.server
from http import HTTPStatus
import socketserver
import os
import json
import shutil
import mimetypes
import random
random.seed()
# import wavemeter

PORT = 8314

JSONTYPE = 'application/json'

COMMAND = 'command'
PARAMETERS = 'parameters'

def get_wavelength(): return 3028.745 + random.random()

commands = {
    'get wavelength':get_wavelength,
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
        data = json.loads(
            self.rfile.read(
                int(
                    self.headers['content-length']
                )
            ).decode('utf-8')
        )
        command = data[COMMAND]
        parameters = data[PARAMETERS]
        data = commands[command](**parameters)
        # uncomment to sniff traffic
        # print(command,parameters,data)
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type',JSONTYPE)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

with http.server.ThreadingHTTPServer(('', PORT), GraphRequestHandler) as httpd:
    print('serving at port', PORT)
    httpd.serve_forever()
