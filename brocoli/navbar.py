"""
Navigation bar
"""

from six import print_
from six.moves import tkinter as tk
from six.moves import tkinter_ttk as ttk


class HistoryCombobox(ttk.Combobox):
    def __init__(self, master, initial_path):
        ttk.Combobox.__init__(self, master)

        self.history = []
        if initial_path:
            self.delete(0, tk.END)
            self.insert(0, initial_path)
            self.history_append(initial_path)


    def history_append(self, value):
        if value in self.history:
            self.history.remove(value)
        self.history.append(value)
        self.config(values=self.history)

    def history_limit(self, keep=0):
        self.history = self.history[0:keep]
        self.config(values=self.history)


class NavigationBar(tk.Frame):
    def __init__(self, master, initial_path='', change_path_cb = None):
        tk.Frame.__init__(self, master)

        self.change_path_cb = change_path_cb

        self.refresh_but = tk.Button(self, text='Refresh')
        self.refresh_but.grid(row=0, sticky='w')

        self.path_entry = HistoryCombobox(self, initial_path)
        self.path_entry.grid(row=0, column=1, sticky='ew')
        self.path_entry.bind('<Return>', self.path_changed)
        self.path_entry.bind('<<ComboboxSelected>>', self.path_changed)

        self.columnconfigure(1, weight=1)

    def get_path(self):
        return self.path_entry.get()

    def set_path(self, new_path, clear_history=False):
        if clear_history:
            self.path_entry.history_limit(0)
        self.path_entry.set(new_path)
        self.path_entry.history_append(new_path)

    def path_changed(self, e):
        print_('new path', self.path_entry.get())
        if self.change_path_cb is not None:
            ok, path = self.change_path_cb(self.path_entry.get())
            if not ok:
                self.set_path(path)

        self.path_entry.history_append(path)
