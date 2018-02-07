"""
Progression dialog classes
"""

from six.moves import tkinter as tk
from six.moves import tkinter_ttk as ttk

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
    def __init__(self, parent, opname, **kwargs):
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

    def set(self, value, maximum = 100):
        value = int((100 * value) / maximum)
        if value == self.count.get():
            return

        self.count.set(value)
        self.label.config(text=self.opname + ' progress: {}%'.format(value))
        self.toplevel.update()

    def finish(self):
        self.toplevel.destroy()

def progress_from_generator(master, message, generator):
    """
    Builds a ProgressDialog eveolving from a generator that yields pairs of
    values in the form (current, total)
    """
    progress = ProgressDialog(master, message)

    for p, n in generator:
        progress.set(p, n)

    progress.finish()

def unbounded_progress_from_generator(master, message, generator):
    """
    Builds a ProgressDialog eveolving from a generator yields (no matter what
    the generator yields)
    """
    progress = UnboundedProgressDialog(master, message)

    for _ in generator:
        progress.step(4)

    progress.finish()
