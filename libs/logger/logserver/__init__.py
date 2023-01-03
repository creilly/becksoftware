import os
import beckhttpserver as bhs
from time import time
import datetime as dt
import json

PORT = 8106

LOGGER_PATH_KEY = 'LOGGERPATH'

UNITS, DELTA, CHANNELS, NAME, THEN, HANDLE = 'units', 'delta', 'channels', 'name', 'then', 'handle'

DATA, METADATA = 0, 1

FILE, FOLDER = 0, 1

validators = {
    FILE:os.path.isfile,
    FOLDER:os.path.isdir
}

extensions = {
    DATA:'tsv',
    METADATA:'json'
}

root = os.environ[LOGGER_PATH_KEY]

def get_data_file(groupname,date):
    path = get_path(groupname,date,DATA)
    if not os.path.exists(path):
        return None
    return open(path,'r')

def get_path(groupname,date,mode):
    return os.path.join(
        get_folder(groupname,date),
        get_fname(date,mode)
    )

def get_folder(groupname,date):
    return os.path.join(
        root,groupname,*[
            '{{:%{}}}'.format(c).format(date)
            for c in ('Y','m')
        ]
    )

def get_fname(date,mode):
    return '{:%d}.{}'.format(date,extensions[mode])

def update(group,now):
    if now < group[THEN]:
        return
    print(now,group[NAME])
    group[THEN] = now + dt.timedelta(seconds=group[DELTA])
    folder = get_folder(group[NAME],now.date())
    if not os.path.exists(folder):
        os.makedirs(folder)
    metadatapath = get_path(group[NAME],now.date(),METADATA)
    if not os.path.exists(metadatapath):
        with open(metadatapath,'w') as f:
            f.write(
                json.dumps(
                    {
                        key:group[key] for key in (CHANNELS,DELTA,UNITS)
                    },
                    indent=2,
                    sort_keys=True
                )
            )
    datapath = get_path(group[NAME],now.date(),DATA)
    with open(datapath,'a') as f:
        f.write(
            '\t'.join(
                map(
                    str,
                    [now.time()] + group[HANDLE]()
                )
            ) + '\n'
        )

def get_items(folder,mode):
    return [
        f for f in
        sorted(os.listdir(folder))
        if validators[mode](os.path.join(folder,f))
    ]

def get_folders(folder):
    return get_items(folder,FOLDER)

def get_files(folder):
    return get_items(folder,FILE)

def get_groups():
    return get_folders(root)

def get_years(group):
    return get_folders(os.path.join(root,group))

def get_months(group,year):
    return get_folders(os.path.join(root,group,year))

def get_days(group,year,month):
    return list(
        sorted(
            set(
                os.path.splitext(f)[0] for f in
                get_files(os.path.join(root,group,year,month))
            )
        )
    )

def get_metadata(group,date):
    return json.load(open(get_path(group,date,METADATA),'r'))

def get_channels(group,date):
    return get_metadata(group,date)[CHANNELS]

def get_delta(group,date):
    return get_metadata(group,date)[DELTA]

def get_units(group,date):
    return get_metadata(group,date)[UNITS]

class LoggerError(Exception):
    pass

class LoggerApp(bhs.BeckApp):
    def __init__(self,groups):
        now = dt.datetime.now()
        for group in groups:
            group[THEN] = now
        self.groups = groups
                
    def loop(self):        
        now = dt.datetime.now()
        for group in self.groups:
            update(group,now)

    @bhs.command('get-groups')
    def get_groups(self):
        return get_groups()

    @bhs.command('get-years')
    def get_years(self,group):
        return get_years(group)

    @bhs.command('get-months')
    def get_months(self,group,year):
        return get_months(group,year)

    @bhs.command('get-days')
    def get_days(self,group,year,month):
        return get_days(group,year,month)    

    @bhs.command('get-channels')
    def get_channels(self,group,date):
        return get_channels(group,dt.date.fromisoformat(date))

    @bhs.command('get-delta')
    def get_delta(self,group,date):
        return get_delta(group,dt.date.fromisoformat(date))

    @bhs.command('get-units')
    def get_units(self,group,date):
        return get_units(group,dt.date.fromisoformat(date))

    @bhs.command('get-data')
    def get_data(self,group,date,delta,start,end):
        d = dt.date.fromisoformat(date)
        data = get_data_file(group,d)
        if data is None:
            return None
        to, tp = [
            dt.time.fromisoformat(s) if s is not None else None
            for s in (start,end)
        ]
        lines = []
        tpp = None
        deltat = dt.timedelta(seconds=delta)
        with data:
            for line in data.readlines():
                raw_fields = line.split('\t')
                t = dt.time.fromisoformat(raw_fields[0])
                if to is None or t > to:
                    if tp is None or tp >= t:
                        if tpp is None or t > tpp:
                            lines.append(
                                [
                                    foo(rf) for rf, foo in zip(
                                        raw_fields,
                                        [str]+[float]*(len(raw_fields)-1)
                                    )
                                ]
                            )
                            _dt = dt.datetime.combine(d,t) + deltat
                            _d = _dt.date()
                            if _d != d:
                                break
                            tpp = _dt.time()
                    else:
                        break
        return lines
    
