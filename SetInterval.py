import threading

class setInterval():
    def __init__(self, func, sec):
        def func_wrapper():
            self.t = threading.Timer(sec, func_wrapper)
            self.t.start()
            func()
        self.t = threading.Timer(sec, func_wrapper)
        self.t.start()

    def cancel(self):
        self.t.cancel()
