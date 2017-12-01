import six
from six import print_
from six.moves import tkinter as tk

from catabrowse.treewidget import TreeWidget
from catabrowse import catalog

def application(path, catalog_):
    root = tk.Tk()

    menubar = tk.Menu(root)

    menubar.add_command(label="Quit!", command=root.quit)
    root.config(menu=menubar)

    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    app = TreeWidget(root, catalog_, path=path)

    app.mainloop()

if __name__ == '__main__':
    import argparse
    import logging
    import sys
    import os

    from catabrowse.irodscatalog import make_irods3_catalog

    cat_types = ['os', 'irods', 'irods3']

    parser = argparse.ArgumentParser(description='Browse catalog')
    parser.add_argument('path', metavar='PATH', help='a path in the catalog')
    parser.add_argument('--catalog', metavar='CAT_TYPE', choices=cat_types,
                        default='os', help='a catalog type')

    args = parser.parse_args()

    cat = None
    if args.catalog == 'os':
        cat = catalog.OSCatalog()
    elif args.catalog == 'irods' or args.catalog == 'irods3':
        cat = make_irods3_catalog(os.path.expanduser('~/.irods/.irodsEnv'))

    application(args.path, cat)
