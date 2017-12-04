import six
from six import print_
from six.moves import tkinter as tk
from six.moves import tkinter_tksimpledialog as tksimpledialog
from six.moves import tkinter_ttk as ttk

from catabrowse.treewidget import TreeWidget
from catabrowse import catalog
from catabrowse import preferences

def application(path, catalog_):
    def new_connection():
        dialog = preferences.NewConnectionDialog(root)

        if dialog.result is None:
            return

        config.save_config(dialog.to_config_dict(), update=True)

    def open_preferences():
        prefs = preferences.Preferences(root)

    root = tk.Tk()

    menubar = tk.Menu(root)

    connection_menu = tk.Menu(menubar, tearoff=False)

    connection_menu.add_command(label="New connection", command=new_connection)
    connection_menu.add_command(label="Preferences", command=open_preferences)
    menubar.add_cascade(label='Settings', menu=connection_menu)

    menubar.add_command(label="Quit!", command=root.quit)

    root.config(menu=menubar)

    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    app = TreeWidget(root, catalog_, path=path)

    root.mainloop()

if __name__ == '__main__':
    import argparse
    import logging
    import sys
    import os

    from catabrowse.irodscatalog import make_irods3_catalog

    from catabrowse import config

    parser = argparse.ArgumentParser(description='Browse catalog')
    parser.add_argument('path', metavar='PATH', nargs='?', default=None,
                        help='a path in the catalog')
    parser.add_argument('--connection', metavar='CONNECTION',
                        default=None, help='use connection:CONNECTION '
                        'section in configuration file')

    args = parser.parse_args()

    cfg = config.load_config()

    conn = cfg['connection:' + (args.connection or
                                cfg['SETTINGS']['default_connection'])]

    cat = None
    catalog_type = conn['catalog_type']
    if catalog_type == 'os':
        cat = catalog.OSCatalog()
    elif catalog_type == 'irods3':
        cat = make_irods3_catalog(os.path.expanduser('~/.irods/.irodsEnv'))

    application(args.path or conn['root_path'], cat)
