import monitron, lockin
from monitron.monitronserver import MonitronApp
import beckhttpserver as bhs
import os

with lockin.LockinHandler() as lih:
    bhs.run_beck_server(
        monitron.PORT,os.path.dirname(__file__),MonitronApp,lih,_debug=False
    )