from datetime import datetime as dt
import json
import os

def get_fname(desc,ext,folder=None,metadata=None):
    fname_fmt = '{}-{}.{{}}'.format(
        dt.now().strftime('%y%m%d%H%M%S%f'),
        desc
    )
    if folder is not None:
        fname_fmt = os.path.join(folder,fname_fmt)
    if metadata is not None:
        md_fname = fname_fmt.format('json')
        with open(md_fname,'w') as f:
            json.dump(metadata,f,indent=4)
    return fname_fmt.format(ext)
