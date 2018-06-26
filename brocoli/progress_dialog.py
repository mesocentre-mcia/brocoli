"""
Progression dialog classes
"""

from six.moves import tkinter as tk
from six.moves import tkinter_ttk as ttk
from six import print_

class UnboundedProgressDialog:
    """
    Displays a progression dialog without information on the completion of the
    task but with simple feeling of something evolving
    """
    def __init__(self, parent, opname, **kwargs):
        self.toplevel = tk.Toplevel(parent, **kwargs)
        self.toplevel.title(opname)
        self.toplevel.transient(parent)

        self.opname = opname

        self.label = tk.Label(self.toplevel, text=opname)
        self.label.pack()

        self.progress = ttk.Progressbar(self.toplevel, orient='horizontal',
                                        mode='indeterminate')

        self.progress.pack(expand=True, fill=tk.BOTH, side=tk.TOP)

    def step(self, speed=1):
        self.progress.step(speed)
        self.toplevel.update()

    def finish(self):
        self.toplevel.destroy()


class ProgressDialog:
    """
    Displays a dialog with a completion percentage
    """
    def __init__(self, parent, opname, interrupt=True, **kwargs):
        self.maximum = 100
        self.toplevel = tk.Toplevel(parent, **kwargs)
        self.toplevel.title(opname)
        self.toplevel.transient(parent)

        self.opname = opname

        self.count = tk.IntVar()

        self.label = tk.Label(self.toplevel, text=opname + ' progress: 0%')
        self.label.pack()

        self.count.set(-1)

        self.progress = ttk.Progressbar(self.toplevel, orient='horizontal',
                                        mode='determinate',
                                        variable=self.count,
                                        maximum=self.maximum)

        self.progress.pack(expand=True, fill=tk.BOTH, side=tk.TOP)
        self.interrupted = False
        if interrupt:
            interrupt_btn = tk.Button(self.toplevel, text='Interrupt',
                                      command=self.interrupt)
            interrupt_btn.pack()

    def interrupt(self):
        self.interrupted = True

    def set_message(self, message=None, percent=0):
        if message is not None:
            self.opname = message
        self.label.config(text=self.opname + ' progress: {}%'.format(percent))

    def set(self, value, maximum=100):
        value = int((100 * value) / maximum)
        if value == self.count.get():
            self.toplevel.update()
            return

        self.count.set(value)
        self.set_message(percent=value)
        self.toplevel.update()

    def finish(self):
        self.toplevel.destroy()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.finish()


def progress_from_generator(master, message, generator):
    """
    Builds a ProgressDialog evolving from a generator that yields pairs of
    values in the form (current, total)
    """
    with ProgressDialog(master, message) as progress:
        for p, n in generator:
            progress.set(p, n)

            if progress.interrupted:
                return


def unbounded_progress_from_generator(master, message, generator):
    """
    Builds a ProgressDialog evolving from a generator yields (no matter what
    the generator yields)
    """
    with UnboundedProgressDialog(master, message) as progress:
        for _ in generator:
            progress.step(4)
