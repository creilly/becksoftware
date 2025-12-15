import beckhttpserver as bhs

class AlertApp(bhs.BeckApp):
    def __init__(self):
        self.alert = None        

    @bhs.command('get alert')
    def get_alert(self):
        return self.alert
    
    @bhs.command('set alert')
    def set_alert(self,alert):
        self.alert = alert
    
    @bhs.command('clear alert')
    def clear_alert(self):
        self.alert = None