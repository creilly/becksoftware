import beckhttpserver as bhs, os
from srschopper import PORT
from srschopper.device import SRSChopperHandler
from srschopper.server import SRSChopperApp

with SRSChopperHandler() as srsch:    
    bhs.run_beck_server(PORT,os.path.dirname(__file__),SRSChopperApp,srsch,_debug=False)