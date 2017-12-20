from . import catalog
from . progress_dialog import progress_from_generator as progress
from . progress_dialog import unbounded_progress_from_generator as uprogress
from . import exceptions

import six
from six import print_

from six.moves import tkinter as tk
from six.moves import tkinter_tkfiledialog as filedialog
from six.moves import tkinter_tksimpledialog as simpledialog
from six.moves import tkinter_ttk as ttk
from six.moves import tkinter_messagebox as messagebox

import collections


def handle_catalog_exceptions(method):
    """
    Method decorator that presents Brocoli exceptions to the user with messages
    """
    def method_wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except exceptions.ConnectionError as e:
            messagebox.showerror('Catalog Connection Error',
                                 ('Connection failed: ' +
                                  '{}').format(str(e)))
        except exceptions.FileNotFoundError as e:
            messagebox.showerror('File Not Found',
                                 ('Catalog file was not found: ' +
                                  '{}').format(str(e)))
        except Exception as e:
            messagebox.showerror('Unknown Error',
                                 ('Some unknown exception occurred: ' +
                                  '{}').format(str(e)))

    return method_wrapper


class ColumnDef(object):
    def __init__(self, name, text, anchor = 'w'):
        self.name = name
        self.text = text
        self.anchor = anchor


class TreeWidget(tk.Frame):
    """
    The main Brocoli widget displaying Catalog directory contents inside a
    ttk.TreeView
    """
    __placeholder_prefix = '__placeholder_'
    __empty_prefix = '__empty_'
    __context_menu_upload = 'Upload local files'
    __context_menu_upload_directory = 'Recursive upload'
    __context_menu_download = 'Download to local disk'
    __context_menu_delete = 'Delete'
    __context_menu_mkdir = 'New directory'

    columns_def = collections.OrderedDict([
        ('#0', ColumnDef('#0', 'path')),
        ('user', ColumnDef('user', 'owner')),
        ('size', ColumnDef('size', 'size')),
        ('nreplicas', ColumnDef('nreplicas', '# of replicas')),
        ('mtime', ColumnDef('mtime', 'modification time')),
    ])

    def __init__(self, master, catalog, path):
        tk.Frame.__init__(self, master)

        self.master = master

        self.columns = [
            'user',
            'size',
            'nreplicas',
            'mtime',
        ]

        self.tree = ttk.Treeview(self, columns=self.columns)

        ysb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        xsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscroll=ysb.set, xscroll=xsb.set)

        for c in ['#0'] + self.columns:
            cd = self.columns_def[c]
            self.tree.heading(c, text=cd.text, anchor=cd.anchor)

        self.tree.bind('<<TreeviewOpen>>', self.open_cb)

        self.tree.grid(row=0, column=0, sticky='nsew')
        ysb.grid(row=0, column=1, sticky='ns')
        xsb.grid(row=1, column=0, sticky='ew')

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.grid(sticky='nsew')

        self._set_context_menu()

        self.set_connection(catalog, path)

    def get_display_columns(self):
        return self.tree.config(cnf='displaycolumns')[-1]

    def set_display_columns(self, columns):
        self.tree.config(displaycolumns=columns)

    def set_connection(self, catalog_factory, path):
        try:
            catalog = catalog_factory(self)

            st = catalog.lstat(path)
            values = [st[k] for k in self.columns]
        except IOError as e:
            if e.errno == exceptions.errno.ENOENT:
                messagebox.showerror('Connection error',
                                     ('Connection root path \'{}\' does ' +
                                      'not exist on catalog').format(path))
                return
        except exceptions.ConnectionError as e:
            messagebox.showerror('Connection error',
                                 ('Connection failed with error: ' +
                                  '{}').format(str(e)))
            return

        self.catalog = catalog
        self.path = path

        for child in self.tree.get_children():
            self.tree.delete(child)

        root_node = self.tree.insert('', 'end', iid=path, text=path,
                                     open=True, values=values)

        self.process_directory(root_node, path)

    def _set_context_menu(self):
        self.context_menu = tk.Menu(self.tree, tearoff=False)

        def _map(e):
            former_sel = self.get_selection()

            def selchanged(e):
                if former_sel != self.get_selection():
                    self.context_menu.unpost()

            self.context_menu_mapped = True
            self.tree.bind('<<TreeviewSelect>>', selchanged)

        def _unmap(e):
            self.context_menu_mapped = False
            self.tree.bind('<<TreeviewSelect>>')

        self.context_menu_mapped = False
        self.context_menu.bind('<Map>', _map)
        self.context_menu.bind('<Unmap>', _unmap)

        self.context_menu.add_command(label=self.__context_menu_mkdir,
                                      command=self.mkdir)
        self.context_menu.add_command(label=self.__context_menu_download,
                                      command=self.download)
        self.context_menu.add_command(label=self.__context_menu_upload,
                                      command=self.upload)
        self.context_menu.add_command(label=self.
                                      __context_menu_upload_directory,
                                      command=self.upload_directory)
        self.context_menu.add_command(label=self.__context_menu_delete,
                                      command=self.delete)

        if (self.tree.tk.call('tk', 'windowingsystem') == 'aqua'):
            self.tree.bind('<2>', self._select_and_pop)
            self.tree.bind('<Control-1>', self._select_and_pop)
        else:
            self.tree.bind('<3>', self._select_and_pop)

    def get_selection(self):
        ret = []

        for e in self.tree.selection():
            if e.startswith('__'):
                continue
            ret.append(e)

        return ret

    def _select_and_pop(self, e):
        item = self.tree.identify_row(e.y)

        if not item:
            return

        selection = self.get_selection()
        if item in selection:
            if self.context_menu_mapped:
                self.context_menu.unpost()
                return
        else:
            if selection and self.context_menu_mapped:
                self.context_menu.unpost()
                return
            self.tree.selection_set(item)

        selection = self.get_selection()
        state = 'disabled'
        if len(selection) == 1:
            item = selection[0]
            is_directory = len(self.tree.get_children(item)) >= 1

            if is_directory:
                state = 'active'

        self.context_menu.entryconfig(self.__context_menu_upload, state=state)
        self.context_menu.entryconfig(self.__context_menu_upload_directory,
                                      state=state)
        self.context_menu.entryconfig(self.__context_menu_mkdir, state=state)

        state = 'active'
        if item.startswith(self.__empty_prefix):
            state = 'disabled'
        self.context_menu.entryconfig(self.__context_menu_download,
                                      state=state)

        self.context_menu.post(e.x_root, e.y_root)

    def _split_files_and_directories(self, selection):
        files = []
        directories = []
        for s in selection:
            if len(self.tree.get_children(s)) > 0:
                directories.append(s)
            else:
                files.append(s)

        return files, directories

    @handle_catalog_exceptions
    def download(self):
        selection = self.get_selection()
        destdir = filedialog.askdirectory()
        if not destdir:
            return

        print_('downloading', selection, 'to', destdir)

        files, directories = self._split_files_and_directories(selection)

        if files:
            progress(self.master, 'download {} files'.format(len(files)),
                     self.catalog.download_files(files, destdir))

        if directories:
            uprogress(self.master,
                      'download {} directories'.format(len(directories)),
                      self.catalog.download_directories(directories, destdir))

    @handle_catalog_exceptions
    def upload(self):
        path = self.get_selection()[0]
        files = filedialog.askopenfilenames()
        if not files:
            return

        print_('uploading', files, 'to', path)
        if files:
            progress(self.master, 'upload {} files'.format(len(files)),
                     self.catalog.upload_files(files, path))

        self.process_directory(path, path)

    @handle_catalog_exceptions
    def upload_directory(self):
        path = self.get_selection()[0]
        directory = filedialog.askdirectory()
        if not directory:
            return

        print_('recursively uploading', directory, 'to', path)

        progress(self.master, 'recursively upload {} directory'.format(1),
                 self.catalog.upload_directories((directory, ), path))

        self.process_directory(path, path)

    @handle_catalog_exceptions
    def delete(self):
        selection = self.get_selection()

        print_('deleting', selection)

        files, directories = self._split_files_and_directories(selection)

        if len(selection) > 0:
            msg = 'Delete '
            msg_list = []
            if len(files) > 0:
                msg_list.append('{} files'.format(len(files)))
            if len(directories) > 0:
                msg_list.append('{} directories'.format(len(directories)))
            msg += ' and '.join(msg_list) + '?'
            if not messagebox.askokcancel('Confirm Delete', msg):
                return

        parents = {self.tree.parent(f) for f in selection}

        if files:
            progress(self.master, 'delete {} files'.format(len(files)),
                     self.catalog.delete_files(files))

        if directories:
            progress(self.master, 'delete {} directories'.format(len(files)),
                     self.catalog.delete_directories(directories))

        for parent in parents:
            self.process_directory(parent, parent)

    @handle_catalog_exceptions
    def mkdir(self):
        parent = self.get_selection()[0]
        name = simpledialog.askstring('Create new directory',
                                      '{} directory name'.format(parent))
        if not name:
            return

        self.catalog.mkdir(self.catalog.join(parent, name))
        self.process_directory(parent, parent)

    def open_cb(self, event):
        iid = self.tree.focus()
        children = self.tree.get_children(iid)
        if len(children) == 1 and \
           children[0].startswith(self.__placeholder_prefix):
            self.process_directory(iid, iid)

    def process_directory(self, parent, path):
        children = self.catalog.listdir(path)

        item_children = self.tree.get_children(parent)
        for child in item_children:
            self.tree.delete(child)

        if not children:
            self.tree.insert(parent, 'end', iid=self.__empty_prefix + path,
                             text='<empty dir>')
            return

        for p in children:
            abspath = self.catalog.join(path, p)
            isdir = self.catalog.isdir(abspath)
            st = self.catalog.lstat(abspath)

            values = [st[k] for k in self.columns]
            oid = self.tree.insert(parent, 'end', iid=abspath, text=p,
                                   open=False, values=values)

            if isdir:
                self.tree.insert(oid, 'end',
                                 iid=self.__placeholder_prefix + abspath)
