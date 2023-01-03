import beckhttpserver as bhs
from logger import logserver as ls
import os
import argparse

ap = argparse.ArgumentParser(description='logger server')
ap.add_argument('--log', action='store_true')
ap.add_argument('--nolog',dest='log',action='store_false')
ap.set_defaults(log=False)
args = ap.parse_args()
if args.log:
    from logger.logserver import groups as lsg
    groups = lsg.groups
else:
    groups = []
    print('warning! logger in read-only mode.')
    print('to run logger in logging mode, run with --log option.')

bhs.run_beck_server(ls.PORT,os.path.dirname(__file__),ls.LoggerApp,groups,_debug=True)
