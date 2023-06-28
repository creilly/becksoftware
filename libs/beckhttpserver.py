# to use this library:
#
# create a subclass of the BeckApp class.
#
# for each http command you want to service,
# create a method that has the http command
# parameter names as function arguments.
#
# then, decorate the method with the command
# decorator, passing in the http command name
# as the argument to the decorator
#
# then, if you want the app to do work in the
# background, define the loop() method. this
# method will be called repeatedly in an endless
# loop, only pausing between loops to service in
# http requests.
#
# to run the server, call:
#
# run_beck_server(port,root_folder,app_class,*args,**kwargs)
#
# where:
#
# * port is the port number you want to serve from
# * root_folder is the folder with which GET requests
#   will be referenced.
#   GET requests are just meant to serve static files.
# * app_class is the name of the class you created in
#   the earlier steps
# * *args and **kwargs are extra arguments which will be
#   passed to the constructor of your app_class before
#   the server starts serving.
#
# example:
#
# class ExampleApp(BeckApp):
#     def __init__(self,voltmeter,voltage_source):
#         self.voltmeter = voltmeter
#         self.voltage_source = voltage_source
#         self.voltage = 0
#
#     @command('get-voltage'):
#     def get_voltage(self):
#         return self.voltage
#
#     @command('set-voltage'):
#     def set_voltage(self,voltage):
#         self.voltage_source.set_voltage(voltage)
#
#     def loop(self):
#         self.voltage = self.voltmeter.get_voltage()
#
# run_beck_server(8999,'C:\tmp',ExampleApp,nat_inst_voltmeter,agilent_voltage_source)
#
# if an HTTP client sends a POST request (to any url) with json data of:
#
# {"command":"set-voltage", "parameters":{voltage:9.0}}
#
# then the server will call your app's set_voltage command with the
# voltage argument set to 9.0

import http.server
from http import HTTPStatus
import inspect
import json
import shutil
import mimetypes
import os
import signal
import selectors
from socketserver import _ServerSelector
import traceback

JSONTYPE = 'application/json'
COMMAND = 'command'
PARAMETERS = 'parameters'
ERROR = '_error'

COMMANDTAG = '__command'

class BeckApp:
    commands = {}
    def loop(self):
        pass

    def shutdown(self):
        pass

GEN_ERROR = 1
class BeckError(Exception):
    def __init__(self,msg,code=GEN_ERROR):
        self.msg = msg
        self.code = code

def run_beck_server(port,rootfolder,appcls,*args,**kwargs):
    no_interrupt_received = [None]
    def signal_handler(sig, frame):
        no_interrupt_received.pop()
    prev_handler = signal.signal(signal.SIGINT, signal_handler)
    with BeckHTTPServer(port,rootfolder,appcls,*args,**kwargs) as httpd:
        while no_interrupt_received:
            httpd.app.loop()
            httpd.handle_requests()
        httpd.app.shutdown()
        signal.signal(signal.SIGINT, prev_handler)

def command(name):
    def _(method):
        setattr(method,COMMANDTAG,name)
        return method
    return _

def set_commands(appcls):
    for name, method in appcls.__dict__.items():
        if hasattr(method,COMMANDTAG):
            appcls.commands[getattr(method,COMMANDTAG)] = method
    return appcls

def _instance_methodify(fnc):
    def _fnc(self,**kwargs):
        return fnc(**kwargs)
    return _fnc

# for convenience. if it's easier to write your application as a
# a dictionary of command-name:function pairs.
# converts dictionary into a BeckApp object
def create_app(commands):
    class _(BeckApp):
        pass
    for name, fnc in commands.items():
        setattr(
            _,
            name.replace('-','_'),
            command(name)(_instance_methodify(fnc))
        )
    return _
    
DEF_INTERFACE = ''
class BeckHTTPServer(http.server.HTTPServer):
    commands = {}
    _DEBUG = '_debug'
    _INTERFACE = '_interface'
    def __init__(self,port,rootfolder,appcls,*args,**kwargs):
        if self._DEBUG in kwargs:
            self._debug = kwargs.pop(self._DEBUG)
        else:
            self._debug = True
        if self._INTERFACE in kwargs:
            interface = kwargs.pop(self._DEBUG)
        else:
            interface = DEF_INTERFACE
        self.rootfolder = rootfolder
        self.app = set_commands(appcls)(*args,**kwargs)
        super().__init__((interface,port),BeckRequestHandler)

    def handle_requests(self):
        with _ServerSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            while selector.select(0):
                self._handle_request_noblock()

def check_path(folder,path):    
    realfolder = os.path.realpath(folder) 
    realpath = os.path.realpath(path)         
    matches = realfolder == os.path.commonpath((realfolder,realpath)) 
    # print('folder',folder)
    # print('path',path)
    # print('real folder',realfolder)
    # print('real path',realpath)
    # print('matches',matches)
    # print('matches',matches)
    return matches

class BeckRequestHandler(http.server.BaseHTTPRequestHandler):
    def format_relative_path(self,relative_path):
        return os.path.join(
            self.server.rootfolder,
            relative_path
        )

    def check_path(self,path):
        return check_path(self.server.rootfolder,path)        
        
    def do_GET(self):
        path = self.path.split('/',1)[1]
        if not path:
            path = 'index.html'
        path = self.format_relative_path(path)
        if not self.check_path(path):
            self.send_error(HTTPStatus.UNAUTHORIZED)
        if os.path.isfile(path):
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type',mimetypes.guess_type(path)[0])
            self.end_headers()
            shutil.copyfileobj(open(path,'rb'),self.wfile)
            return
        else:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

    def do_POST(self):
        rawdata = self.rfile.read(
            int(
                self.headers['content-length']
            )
        ).decode('utf-8')
        data = json.loads(rawdata)
        command = data[COMMAND]
        parameters = data[PARAMETERS]
        try:
            response = self.server.app.commands[command](self.server.app,**parameters)  
        except BeckError as be:
            response = {ERROR:[be.code,be.msg]}
        except Exception as e:
            response = {
                ERROR:traceback.format_exc()
            }
        if self.server._debug:
            print('command received:')
            print(
                '\n'.join(
                    '\t{}:\t{}'.format(name,value)
                    for name, value in
                    (
                        ('commmand','"{}"'.format(command)),
                        ('parameters',str(parameters))
                    )
                )
            )
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type',JSONTYPE)
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def log_message(self,*args,**kwargs):
        if self.server._debug:
            super().log_message(*args,**kwargs)

