import http.client
import json
from beckhttpserver import BeckError, ERROR

JSONTYPE = 'application/json'
COMMAND = 'command'
PARAMETERS = 'parameters'

def send_command(host,port,command,parameters):
    conn = http.client.HTTPConnection(host,port)
    body = json.dumps(
        {
            COMMAND:command,
            PARAMETERS:parameters
        }
    )
    headers = {
        'Content-type': JSONTYPE,
        'Accept': JSONTYPE
    }
    conn.request('POST','',body,headers)
    response = json.loads(conn.getresponse().read())
    if type(response) is dict and ERROR in response:
        raise BeckError(response[ERROR])
    return response
