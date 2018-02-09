from . import catalog
from . progress_dialog import progress_from_generator as progress
from . progress_dialog import unbounded_progress_from_generator as uprogress
from . import exceptions
from . import navbar
from . listmanager import ColumnDef

import six
from six import print_

from six.moves import tkinter as tk
from six.moves import tkinter_tkfiledialog as filedialog
from six.moves import tkinter_tksimpledialog as simpledialog
from six.moves import tkinter_ttk as ttk
from six.moves import tkinter_messagebox as messagebox

import collections
import re
import traceback


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
            print_(traceback.format_exc())


    return method_wrapper


class TreeWidget(tk.Frame):
    """
    The main Brocoli widget displaying Catalog directory contents inside a
    ttk.TreeView
    """
    __placeholder_prefix = '__placeholder_'
    __empty_prefix = '__empty_'
    __dot_prefix = 'dot_'
    __dotdot_prefix = 'dotdot_'

    __prefix_path_re = re.compile('^(?P<prefix>{})(?P<suffix>.*)$'.format('|'.join([
        __placeholder_prefix,
        __empty_prefix,
        __dot_prefix,
        __dotdot_prefix,
    ])))
    __context_menu_upload = 'Upload local files'
    __context_menu_upload_directory = 'Recursive upload'
    __context_menu_download = 'Download to local disk'
    __context_menu_delete = 'Delete'
    __context_menu_mkdir = 'New directory'
    __context_menu_goto = 'Go to'
    __context_menu_properties = 'Properties'

    columns_def = collections.OrderedDict([
        ('#0', ColumnDef('#0', 'path')),
        ('user', ColumnDef('user', 'owner')),
        ('size', ColumnDef('size', 'size')),
        ('nreplicas', ColumnDef('nreplicas', '# of replicas')),
        ('mtime', ColumnDef('mtime', 'modification time')),
    ])

    def __init__(self, master):
        tk.Frame.__init__(self, master)

        self.master = master
        self.root_path = ''

        self.catalog = None
        self.path = None

        self.columns = [
            'user',
            'size',
            'nreplicas',
            'mtime',
        ]

        self.navigation_bar = navbar.NavigationBar(self, self.root_path,
                                                   self.set_path)
        self.navigation_bar.refresh_but.config(command=self.refresh)

        self.navigation_bar.grid(row=0, columnspan=2, sticky='ew')

        self.tree = ttk.Treeview(self, columns=self.columns)

        ysb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        xsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscroll=ysb.set, xscroll=xsb.set)

        for c in ['#0'] + self.columns:
            cd = self.columns_def[c]
            self.tree.heading(c, text=cd.text, anchor=cd.anchor)

        self.tree.bind('<<TreeviewOpen>>', self.open_cb)

        self.tree.grid(row=1, column=0, sticky='nsew')
        ysb.grid(row=1, column=1, sticky='ns')
        xsb.grid(row=2, column=0, sticky='ew')

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self._set_context_menu()

    def get_display_columns(self):
        return self.tree.config(cnf='displaycolumns')[-1]

    def set_display_columns(self, columns):
        if columns is None:
            columns = list(self.columns)

        self.tree.config(displaycolumns=columns)

    def set_connection(self, catalog_factory, path):
        try:
            # build catalog
            catalog = catalog_factory(self)

            if catalog is None:
                # user must have cancelled something
                return False

            path = catalog.normpath(path)

            # verify root path is valid
            if not catalog.isdir(path):
                messagebox.showerror('Path error',
                                     ('Path \'{}\' is not a ' +
                                      'directory').format(path))
                return False
        except IOError as e:
            if e.errno == exceptions.errno.ENOENT:
                messagebox.showerror('Connection error',
                                     ('Connection root path \'{}\' does ' +
                                      'not exist on catalog').format(path))
                return False
        except exceptions.ConnectionError as e:
            messagebox.showerror('Connection error',
                                 ('Connection failed with error: ' +
                                  '{}').format(str(e)))
            return False

        self.catalog = catalog
        self.root_path = path

        self.set_path(path, clear_history=True)

        return True

    def set_path(self, path, clear_history=False):
        if path == self.path:
            return True, self.path

        try:
            if not self.catalog.isdir(path):
                messagebox.showerror('Path error',
                                     ('Path \'{}\' is not a ' +
                                      'directory').format(path))
                return False, self.path

        except IOError as e:
            if e.errno == exceptions.errno.ENOENT:
                messagebox.showerror('Connection error',
                                     ('Path \'{}\' does ' +
                                      'not exist on catalog').format(path))
                return False, self.path

            raise

        self.path = path

        self.navigation_bar.set_path(self.path, clear_history)

        self.refresh()

        return True, self.path

    def refresh(self):
        print_('refresh', self.path)

        for child in self.tree.get_children():
            self.tree.delete(child)

        self.process_directory('', self.path)

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

        self.context_menu.add_command(label=self.__context_menu_goto,
                                      command=self.goto_selected)

        self.context_menu.add_command(label=self.__context_menu_properties,
                                      command=self.selected_properties)

        self.tree.bind('<Double-Button-1>', self._goto, add='+')

        if (self.tree.tk.call('tk', 'windowingsystem') == 'aqua'):
            self.tree.bind('<Button-2>', self._select_and_pop)
            self.tree.bind('<Control-Button-1>', self._select_and_pop)
        else:
            self.tree.bind('<Button-3>', self._select_and_pop)

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
                self.tree.selection_set(item)
                return
            self.tree.selection_set(item)

        selection = self.get_selection()
        state = tk.DISABLED
        is_directory = False
        if len(selection) == 1:
            item = selection[0]
            is_directory = (len(self.tree.get_children(item)) >= 1 or
                            item.startswith(self.__dot_prefix) or
                            item.startswith(self.__dotdot_prefix))

            if is_directory:
                state = tk.ACTIVE

        self.context_menu.entryconfig(self.__context_menu_upload, state=state)
        self.context_menu.entryconfig(self.__context_menu_upload_directory,
                                      state=state)
        self.context_menu.entryconfig(self.__context_menu_mkdir, state=state)

        self.context_menu.entryconfig(self.__context_menu_goto, state=state)

        state = tk.ACTIVE
        if (item.startswith(self.__empty_prefix) or
                item.startswith(self.__dotdot_prefix)):
            state = tk.DISABLED

        self.context_menu.entryconfig(self.__context_menu_download,
                                      state=state)

        state = tk.ACTIVE
        if (item.startswith(self.__dot_prefix) or
                item.startswith(self.__dotdot_prefix)):
            state = tk.DISABLED

        self.context_menu.entryconfig(self.__context_menu_delete,
                                      state=state)

        self.context_menu.post(e.x_root, e.y_root)

    def item_path(self, item):
        m = TreeWidget.__prefix_path_re.match(item)
        if m is None:
            return item

        return m.group('suffix')


    def _goto(self, e):
        item = self.tree.identify_row(e.y)
        if not item or not item.startswith(TreeWidget.__dotdot_prefix):
            return

        self.set_path(self.catalog.dirname(self.path))

    def _split_files_and_directories(self, selection):
        files = []
        directories = []
        for s in selection:
            s = self.item_path(s)
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
            progress(self.master,
                     'download {} directories'.format(len(directories)),
                     self.catalog.download_directories(directories, destdir))

    @handle_catalog_exceptions
    def upload(self):
        path = self.item_path(self.get_selection()[0])
        files = filedialog.askopenfilenames()
        if not files:
            return

        print_('uploading', files, 'to', path)
        if files:
            progress(self.master, 'upload {} files'.format(len(files)),
                     self.catalog.upload_files(files, path))

        pathid = path
        if path == self.path:
            pathid = ''
        self.process_directory(pathid, path)

    @handle_catalog_exceptions
    def upload_directory(self):
        path = self.item_path(self.get_selection()[0])
        directory = filedialog.askdirectory()
        if not directory:
            return

        print_('recursively uploading', directory, 'to', path)

        progress(self.master, 'recursively upload {} directory'.format(1),
                 self.catalog.upload_directories((directory, ), path))

        pathid = path
        if path == self.path:
            pathid = ''
        self.process_directory(pathid, path)

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

        if '' in parents:
            self.process_directory('', self.path)
        else:
            for parent in parents:
                self.process_directory(parent, parent)

    @handle_catalog_exceptions
    def mkdir(self):
        selected = self.get_selection()[0]
        parent = self.item_path(selected)
        name = simpledialog.askstring('Create new directory',
                                      '{} directory name'.format(parent))
        if not name:
            return

        new_dir = self.catalog.join(parent, name)
        self.catalog.mkdir(new_dir)

        if selected.startswith(TreeWidget.__dot_prefix):
            selected = ''
        elif not self.tree.item(selected, option='open'):
            # non root closed directory parent needs to be open for display
            self.process_directory(selected, parent)
            self.tree.item(selected, open=True)
            return

        if self.__empty_prefix + parent in self.tree.get_children(selected):
            self.tree.delete(self.__empty_prefix + parent)

        st = self.catalog.lstat(new_dir)
        self.__fill_item(selected, parent, name, st)

    def goto_selected(self):
        selected = self.get_selection()[0]
        path = self.item_path(selected)
        print_('go to', elected, path)
        self.set_path(path)

    def selected_properties(self):
        selected = self.get_selection()[0]
        path = self.item_path(selected)

        props = None
        entry_type = ''
        if len(self.tree.get_children(selected)) > 0 or selected != path:
            # directories have children or their iid is different from their path
            props = self.catalog.directory_properties(path)
            entry_type = 'Directory'
        else:
            # file properties
            props = self.catalog.file_properties(path)
            entry_type = 'File'

        if props is None or len(props) == 0:
            return

        tl = tk.Toplevel(self.master)
        tl.title(entry_type + ' properties: ' + path)

        nb = ttk.Notebook(tl)
        nb.pack(fill=tk.BOTH, expand=1)

        for t, p in props.items():
            nb.add(p.get_widget(nb), text=t, sticky='nsew')

        tl.wait_window()

    def open_cb(self, event):
        iid = self.tree.focus()
        children = self.tree.get_children(iid)
        if len(children) == 1 and \
           children[0].startswith(self.__placeholder_prefix):
            self.process_directory(iid, iid)

    def __fill_item(self, parent, path, name, st):
        abspath = self.catalog.join(path, name)

        values = [st[k] for k in self.columns]
        oid = self.tree.insert(parent, 'end', iid=abspath, text=name,
                               open=False, values=values)

        if st['isdir']:
            self.tree.insert(oid, 'end',
                             iid=self.__placeholder_prefix + abspath)

    def process_directory(self, parent, path):

        entries = self.catalog.listdir(path)

        item_children = self.tree.get_children(parent)
        for child in item_children:
            self.tree.delete(child)

        if parent == '':
            if path != self.root_path:
                ppath = self.catalog.dirname(path)
                self.tree.insert(parent, 'end',
                                 iid=self.__dotdot_prefix + ppath,
                                 text='..')
            self.tree.insert(parent, 'end', iid=self.__dot_prefix + path,
                             text='.')

        if not entries:
            self.tree.insert(parent, 'end', iid=self.__empty_prefix + path,
                             text='<empty dir>')
            return

        for k, v in entries.items():
            self.__fill_item(parent, path, k, v)
