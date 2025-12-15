import beckhttpserver as bhs, os
from alerter import PORT
from alerter.server import AlertApp

bhs.run_beck_server(PORT,os.path.dirname(__file__),AlertApp,_debug=False)