import beckhttpclient as bhc
from logger import logserver
import datetime as dt

HOST = bhc.get_host()
PORT = logserver.PORT

def send_command(command,parameters):
    return bhc.send_command(HOST,PORT,command,parameters)

def get_data(group,date,delta,start=None,end=None):
    params = {'group':group,'delta':delta}
    params.update(
        {
            pname:(param.isoformat() if param is not None else None)
            for pname, param in (
                ('date',date),
                ('start',start),
                ('end',end)
            )
        }
    )
    return send_command('get-data',params)

def get_delta(group,date):
    return send_command('get-delta',{'group':group,'date':date.isoformat()})

if __name__ == '__main__':
    print(
        get_data(
            'pfeiffer',
            dt.date(year=2022,month=3,day=16),
            1000
        )
    )
