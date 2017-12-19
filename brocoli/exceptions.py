import os
import errno


class BrocoliError(Exception):
    def __init__(self, exception):
        self.exception = exception

    def __str__(self):
        return type(self.exception).__name__ + ': ' + str(self.exception)


class ConnectionError(BrocoliError):
    pass

class FileNotFoundError(BrocoliError):
    pass


def ioerror(no):
    return IOError(no, os.strerror(no))

