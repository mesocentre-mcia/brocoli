#!/usr/bin/env python

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

# Brocoli version string
__version__ = '0.2.0'


class ConnectionSwitcher:
    """
    Provides a method that can be used to switch to a particular connection
    """
    def __init__(self, app, conn_name):
        self.app = app
        self.conn_name = conn_name

    def switch(self):
        self.app.set_connection(self.conn_name)


class SwitcherSubmenu:
    """
    A menu containing a list of connections to switch to
    """
    def __init__(self, connection_menu, app):
        self.app = app
        self.menu = connection_menu
        self.menu_name = 'Switch connection'

        self.menu.add_cascade(label=self.menu_name, menu=None)

    def populate(self):
        index = self.menu.index(self.menu_name)
        self.menu.delete(index)

        switch_menu = tk.Menu(self.menu, tearoff=False)

        for c in self.app.cfg.connection_names():
            cs = ConnectionSwitcher(self.app, c)
            switch_menu.add_command(label=c, command=cs.switch)

        self.menu.insert_cascade(index, label=self.menu_name,
                                 menu=switch_menu)


class BrocoliApplication(object):
    def __init__(self, cfg, connection_name):
        # run Tk
        self.root = tk.Tk()

        self.cfg = cfg

        # get connection
        self.cat, root_path = cfg.connection(connection_name)

        self.path = root_path

        # create menus
        self.menubar = tk.Menu(self.root)

        self.connection_menu = tk.Menu(self.menubar, tearoff=False)

        self.menubar.add_cascade(label='Settings', menu=self.connection_menu)

        self.menubar.add_command(label="Quit!", command=self.root.quit)

        self.root.config(menu=self.menubar)

        # main window tree view, populate connection menu
        self.tree_widget = TreeWidget(self.root)
        self.tree_widget.grid(sticky='nsew')

        self.set_display_columns()

        self.connection_menu.add_command(label="New connection",
                                         command=self.new_connection)

        self.ss = SwitcherSubmenu(self.connection_menu, self)
        self.ss.populate()

        self.connection_menu.add_command(label="Preferences",
                                         command=self.open_preferences)

        # layout
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.set_connection(connection_name)

    def run(self):
        self.root.mainloop()

    def set_display_columns(self):
        dcols = self.cfg[config.SETTINGS].get('display_columns', None)
        if dcols is not None:
            dcols = dcols.split(',')

        self.tree_widget.set_display_columns(dcols)

    def new_connection(self):
        dialog = preferences.ConnectionConfigDialog(self.root)

        if dialog.result is None:
            return

        config.save_config(dialog.to_config_dict(), update=True)
        self.cfg = config.load_config()
        self.ss.populate()

    def open_preferences(self):
        prefs = preferences.Preferences(self.root)
        if prefs.changed:
            self.cfg = prefs.cfg
            self.ss.populate()

            self.set_display_columns()

    def set_connection(self, connection_name):
        conn, path = self.cfg.connection(connection_name)
        if self.tree_widget.set_connection(conn, path):
            self.root.title('Brocoli - ' + (connection_name or self.cfg.default_connection_name()))


def main():
    """
    Main function for the Brocoli application. Handles command line arguments
    and loads configuration before launching the application window
    """

    parser = argparse.ArgumentParser(description='Browse catalog')
    parser.add_argument('--connection', metavar='CONNECTION',
                        default=None, help='use [connection:CONNECTION] '
                        'section in configuration file')

    args = parser.parse_args()

    cfg = config.load_config()

    app = BrocoliApplication(cfg, args.connection)

    app.run()

if __name__ == '__main__':
    main()
