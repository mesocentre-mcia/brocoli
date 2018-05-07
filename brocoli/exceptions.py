import os
import errno
import traceback

from six.moves import tkinter_messagebox as messagebox
from six import print_


class BrocoliError(Exception):
    def __init__(self, exception):
        self.exception = exception

    def __str__(self):
        return type(self.exception).__name__ + ': ' + str(self.exception)


class ConnectionError(BrocoliError):
    pass


class NetworkError(BrocoliError):
    pass


class FileNotFoundError(BrocoliError):
    pass


class CatalogLogicError(BrocoliError):
    pass


def ioerror(no):
    return IOError(no, os.strerror(no))


def handle_catalog_exceptions(method):
    """
    Method decorator that presents Brocoli exceptions to the user with messages
    """
    def method_wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except ConnectionError as e:
            messagebox.showerror('Catalog Connection Error',
                                 ('Connection failed: ' +
                                  '{}').format(str(e)))
        except FileNotFoundError as e:
            messagebox.showerror('File Not Found',
                                 ('Catalog file was not found: ' +
                                  '{}').format(str(e)))
        except CatalogLogicError as e:
            messagebox.showerror('Catalog Logic Error',
                                 ('Catalog logic error occurred: ' +
                                  '{}').format(str(e)))
        except Exception as e:
            messagebox.showerror('Unknown Error',
                                 ('Some unknown exception occurred: ' +
                                  '{}').format(str(e)))
            print_(traceback.format_exc())

    return method_wrapper
