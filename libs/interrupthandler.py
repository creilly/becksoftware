import signal

class InterruptException(Exception):
    pass

class InterruptHandlerSuspender:
    def __init__(self,interrupt_handler):
        self.interrupt_handler = interrupt_handler

    def __enter__(self):
        self.interrupt_handler.unsubscribe()
        return self
    
    def __exit__(self,*args):
        self.interrupt_handler.subscribe()

class InterruptHandler:
    def __init__(self):
        self._interrupt_received = False

    def handle_interrupt(self,signum,sigframe):
        self._interrupt_received = True

    def interrupt_received(self):
        return self._interrupt_received

    def reset_interrupt(self):
        self._interrupt_received = False

    def raise_interrupt(self,reset=True):
        if reset:
            self.reset_interrupt()
        raise InterruptException()

    def subscribe(self):
        self.prev_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT,self.handle_interrupt)

    def unsubscribe(self):
        signal.signal(signal.SIGINT,self.prev_handler)

    def __enter__(self):
        self.subscribe()
        return self

    def __exit__(self,*args):
        self.unsubscribe()        

if __name__ == '__main__':
    from time import sleep
    with InterruptHandler() as ih:
        while not ih.interrupt_received():
            print('press ctrl-c to interrupt loop')            
            sleep(0.5)
        print('interrupt received. stopping program.')