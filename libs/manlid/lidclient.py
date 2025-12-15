from alerter import client as ac
import time

while True:
    try:
        pos = float(input('enter lid angle: '))
        break
    except ValueError:
        continue

P, W = 0, 1

class LidMoving(Exception): pass

def get_moving():
    return ac.get_alert() is not None

def set_lid(new_pos, wait=True):    
    if get_moving():
        raise LidMoving()
    global pos
    if new_pos == pos: return    
    pos = new_pos    
    ac.set_alert('set lid to {:.2f} degs'.format(pos))
    if wait:
        wait_lid()

def get_lid():
    return pos

dt = 0.1
def wait_lid():
    while True:
        if not get_moving(): break
        time.sleep(dt)