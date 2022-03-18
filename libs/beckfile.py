from datetime import datetime as dt

def get_fname(desc,ext):
    return '{}-{}.{}'.format(
        dt.now().strftime('%H%M%S%f'),
        desc,
        ext
    )
