import six
from six import print_
from six.moves import tkinter as tk

from catabrowse.treewidget import TreeWidget
from catabrowse import catalog

def application(path):
    root = tk.Tk()

    menubar = tk.Menu(root)

    menubar.add_command(label="Quit!", command=root.quit)
    root.config(menu=menubar)

    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    app = TreeWidget(root, catalog.OSCatalog(), path=path)

    app.mainloop()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Browse catalog')
    parser.add_argument('path', metavar='PATH', help='a path in the catalog')

    args = parser.parse_args()

    application(args.path)
