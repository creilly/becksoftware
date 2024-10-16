import monitron
from monitron.monitronserver import MonitronApp
import beckhttpserver as bhs
import os

bhs.run_beck_server(monitron.PORT,os.path.dirname(__file__),MonitronApp,_debug=True)