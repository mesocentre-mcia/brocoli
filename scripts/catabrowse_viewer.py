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

    from catabrowse import config

    # usable catalog types
    cat_types = ['os', 'irods', 'irods3']

    parser = argparse.ArgumentParser(description='Browse catalog')
    parser.add_argument('path', metavar='PATH', nargs='?', default=None,
                        help='a path in the catalog')
    parser.add_argument('--profile', metavar='PROFILE',
                        default=None, help='a profile in the configuration file')
    parser.add_argument('--catalog', metavar='CAT_TYPE', choices=cat_types,
                        default=None, help='a catalog type')

    args = parser.parse_args()

    cfg = config.load_config(profile=args.profile)

    cat = None
    catalog_type = args.catalog or cfg['catalog_type']
    if catalog_type == 'os':
        cat = catalog.OSCatalog()
    elif catalog_type in ['irods', 'irods3']:
        cat = make_irods3_catalog(os.path.expanduser('~/.irods/.irodsEnv'))

    application(args.path or cfg['root_path'], cat)
