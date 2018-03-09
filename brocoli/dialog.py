from six import print_
from six.moves import tkinter as tk
from six.moves import tkinter_tksimpledialog as tksimpledialog

class BrocoliDialog(tksimpledialog.Dialog, object):
    def buttonbox(self):
        # tweak to allow body expansion inside the simpledialog
        self.initial_focus.master.pack(padx=5, pady=5, expand=True,
                                       fill=tk.BOTH, side=tk.TOP)
        self.initial_focus.master.columnconfigure(1, weight=1)

        super(BrocoliDialog, self).buttonbox()
