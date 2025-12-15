import beckhttpserver as bhs, os
from shs import PORT
from shs.shserver import SampleHeaterApp
import sampleheater

with sampleheater.SampleHeaterHandler() as sh_handle:
    bhs.run_beck_server(PORT,os.path.dirname(__file__),SampleHeaterApp,sh_handle,_debug=False)