import bologain as bg
from bologain import bologainserver as bgs
import beckhttpserver as bhs
import os

bhs.run_beck_server(bg.PORT,os.path.dirname(__file__),bgs.BoloGainApp,_debug=True)