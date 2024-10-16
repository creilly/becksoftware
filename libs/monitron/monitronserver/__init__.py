import beckhttpserver as bhs, pfeiffer
from monitron import get_input

class MonitronApp(bhs.BeckApp):    
    @bhs.command('get-input')
    def get_input(self):   
        return get_input()