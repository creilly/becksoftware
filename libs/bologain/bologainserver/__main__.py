import bologain as bg
from bologain import bologainserver as bgs
import beckhttpserver as bhs
import os

with bg.BoloGainHandler() as bgh:
    bhs.run_beck_server(bg.PORT,os.path.dirname(__file__),bgs.BoloGainApp,bgh,_debug=True)