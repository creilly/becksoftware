import time
import functools
from beckutil import colorcodes, endcolor, colors as _colors
import sys
from tempfile import SpooledTemporaryFile

def sleep(deltat):
    yield from wait_time(time.time(),deltat)

def wait_time(to,deltat):
    while time.time() - to < deltat:
        yield

def event_loop(
        gens,
        in_hook = None,
        out_hook = None,
        stop_hook = None,
        close_hook = None
    ):
    genpairs = [*enumerate(gens)]
    values = [None] * len(gens)
    try:
        while genpairs:
            to_remove = []
            for genpair in genpairs:
                index, gen = genpair
                try:
                    if in_hook:
                        in_hook(index)                    
                    next(gen)     
                    yield                   
                    if out_hook:
                        out_hook(index)                    
                except StopIteration as si:
                    if stop_hook:
                        stop_hook(index)                    
                    values[index] = si.value
                    to_remove.append(genpair)
            for genpair in to_remove:
                genpairs.remove(genpair)
        return values
    finally:
        for index, gen in enumerate(gens):
            if close_hook:
                close_hook(index)
            gen.close()

def event_loop_logging(gens,colors = None):
    try:        
        stdout = sys.stdout        
        if colors is None:
            colors = [
                _colors[index % len(_colors)]
                for index in range(len(gens))
            ]
        with SpooledTemporaryFile(mode='rw') as f:            
            sys.stdout = f
            def clear_buffer(_):
                f.seek(0)
                f.truncate()                
            def update_log(index):
                f.seek(0)
                text = f.read()
                tabs = '\t' * index                
                if text:
                    tabbed = [
                        tabs + line
                        for line in text.split('\n')
                    ]
                    tabbed[-1] = ''
                    stdout.write(
                        colorcodes[colors[index]] + 
                        '\n'.join(tabbed) + 
                        endcolor
                    )
            return unwind_generator(
                    event_loop(
                    gens,
                    in_hook = clear_buffer,
                    out_hook = update_log,
                    stop_hook = update_log
                )
            )
    finally:
        sys.stdout = stdout
        sys.stdout.write(endcolor)

def get_blocking(async_foo):
    @functools.wraps(async_foo)
    def sync_bar(*args,**kwargs):
        try:
            gen = async_foo(*args,**kwargs)
            while True:
                next(gen)
        except StopIteration as si:
            return si.value
    return sync_bar

def blocking(foo):
    def _blocking(bar):
        return get_blocking(foo)
    return _blocking

def unwind_generator(gen):
    try:
        while True:
            next(gen)
    except StopIteration as si:
        return si.value