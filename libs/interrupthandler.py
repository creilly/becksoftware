import signal

class InterruptHandler:
    def __init__(self):
        self._interrupt_received = False

    def handle_interrupt(self,signum,sigframe):
        self._interrupt_received = True

    def interrupt_received(self):
        return self._interrupt_received

    def reset_interrupt(self):
        self._interrupt_received = False

    def __enter__(self):
        self.prev_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT,self.handle_interrupt)
        return self

    def __exit__(self,*args):
        signal.signal(signal.SIGINT,self.prev_handler)
