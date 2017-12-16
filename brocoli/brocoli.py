#!/usr/bin/env python3

import six
from six import print_
from six.moves import tkinter as tk
from six.moves import tkinter_tksimpledialog as tksimpledialog
from six.moves import tkinter_ttk as ttk

import argparse
import logging
import sys
import os

from . import config
from . treewidget import TreeWidget
from . import catalog
from . import preferences

__version__ = '0.1.0'


class conn_switcher:
    def __init__(self, cfg, app, conn_name):
        self.cfg = cfg
        self.app = app
        self.conn_name = conn_name

    def switch(self):
        self.app.set_connection(*self.cfg.connection(self.conn_name))


class switcher_submenu:
    def __init__(self, cfg, connection_menu, app):
        self.cfg = cfg
        self.app = app
        self.menu = connection_menu
        self.menu_name = 'Switch connection'

        self.menu.add_cascade(label=self.menu_name, menu=None)

    def populate(self):
        index = self.menu.index(self.menu_name)
        self.menu.delete(index)

        switch_menu = tk.Menu(self.menu, tearoff=False)

        for c in self.cfg.connection_names():
            cs = conn_switcher(self.cfg, self.app, c)
            switch_menu.add_command(label=c, command=cs.switch)

        self.menu.insert_cascade(index, label=self.menu_name,
                                 menu=switch_menu)


def application(cfg, connection_name, path):
    def new_connection():
        dialog = preferences.NewConnectionDialog(root)

        if dialog.result is None:
            return

        config.save_config(dialog.to_config_dict(), update=True)
        ss.cfg = config.load_config()
        ss.populate()

    def open_preferences():
        prefs = preferences.Preferences(root)
        if prefs.changed:
            ss.cfg = prefs.connection_manager.cfg
            ss.populate()

    root = tk.Tk()

    cat, root_path = cfg.connection(connection_name)

    app = TreeWidget(root, cat, path=path or root_path)

    menubar = tk.Menu(root)

    connection_menu = tk.Menu(menubar, tearoff=False)

    connection_menu.add_command(label="New connection", command=new_connection)
    switch_menu = None

    ss = switcher_submenu(cfg, connection_menu, app)
    ss.populate()

    connection_menu.add_command(label="Preferences", command=open_preferences)
    menubar.add_cascade(label='Settings', menu=connection_menu)

    menubar.add_command(label="Quit!", command=root.quit)

    root.config(menu=menubar)

    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description='Browse catalog')
    parser.add_argument('path', metavar='PATH', nargs='?', default=None,
                        help='a path in the catalog')
    parser.add_argument('--connection', metavar='CONNECTION',
                        default=None, help='use [connection:CONNECTION] '
                        'section in configuration file')

    args = parser.parse_args()

    cfg = config.load_config()

    application(cfg, args.connection, args.path)

if __name__ == '__main__':
    main()