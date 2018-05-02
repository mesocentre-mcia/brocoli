
from six import print_
from six.moves import tkinter as tk
from six.moves import tkinter_ttk as ttk

import collections
import copy

from . import form
from . dialog import BrocoliDialog


class ColumnDef(object):
    def __init__(self, name, text, anchor='w', form_field=None, display=True):
        self.name = name
        self.text = text
        self.anchor = anchor
        self.form_field = form_field
        self.display = display


class ItemConfigDialog(BrocoliDialog):
    def __init__(self, master, item_fields, item_config=None, **kwargs):
        self.item_fields = item_fields
        self.item_config = item_config

        for ff in self.item_fields.values():
            ff.reset()

        super(ItemConfigDialog, self).__init__(master, **kwargs)

    def body(self, master):
        if self.item_config is not None:
            for k, ff in self.item_fields.items():
                if k in self.item_config:
                    ff.from_string(self.item_config[k])
                    ff.contents_from_config(self.item_config)

        self.item_frame = form.FormFrame(master)
        self.item_frame.grid_fields(self.item_fields.values(), False)
        self.item_frame.grid(row=0, column=1, sticky='nsew')
        self.item_frame.columnconfigure(1, weight=1)

        self.result = None

        return self.item_frame

    def apply(self):
        self.result = collections.OrderedDict()

        for k, ff in self.item_fields.items():
            self.result[k] = ff.to_string()
            self.result.update(ff.get_contents())

class ListManager(tk.Frame):
    def __init__(self, master, columns_def, add_cb=None, remove_cb=None,
                 edit_cb=None):
        tk.Frame.__init__(self, master)

        self.master = master
        self.columns_def = columns_def

        self.fields = collections.OrderedDict([
            (k, cd.form_field) for k, cd in self.columns_def.items()
        ])

        self.items = None

        column_ids = [
            k for k, cd in self.columns_def.items() if cd.display and k != '#0'
        ]

        self.tree = ttk.Treeview(self, columns=column_ids, selectmode='browse')

        ysb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        xsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscroll=ysb.set, xscroll=xsb.set)

        for c in ['#0'] + column_ids:
            cd = self.columns_def[c]
            self.tree.heading(c, text=cd.text, anchor=cd.anchor)

        self.tree.grid(row=0, column=0, sticky='nsew')
        ysb.grid(row=0, column=1, sticky='ns')
        xsb.grid(row=1, column=0, sticky='ew')

        butbox = tk.Frame(self)
        butbox.grid(row=0, column=2, sticky='ns')

        self.newbut = None
        self.removebut = None
        self.editbut = None
        self.duplicatebut = None

        self.add_cb = add_cb
        if add_cb is not None:
            self.newbut = tk.Button(butbox, text='Add', command=self.add)
            self.newbut.grid(row=0, column=0, sticky='ew')

        self.remove_cb = remove_cb
        if remove_cb is not None:
            self.removebut = tk.Button(butbox, text='Remove',
                                       command=self.remove, state=tk.DISABLED)
            self.removebut.grid(row=1, column=0, sticky='ew')

        self.edit_cb = edit_cb
        if edit_cb is not None:
            self.editbut = tk.Button(butbox, text='Edit', command=self.edit,
                                     state=tk.DISABLED)
            self.editbut.grid(row=2, column=0, sticky='ew')

            self.duplicatebut = tk.Button(butbox, text='duplicate',
                                          command=self.duplicate,
                                          state=tk.DISABLED)
            self.duplicatebut.grid(row=3, column=0, sticky='ew')

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.grid(sticky='nsew')

        self.tree.bind('<<TreeviewSelect>>', self.selchanged)

    def populate(self, rows):
        for child in self.tree.get_children():
            self.tree.delete(child)

        self.items = collections.OrderedDict([(v.get('iid', v['#0']), v) for v in rows])

        for v in rows:
            values = [v[c] for c in self.columns_def if c != '#0' and c != 'iid']
            iid = v.get('iid', v['#0'])
            print_("populate", v, iid)
            root_node = self.tree.insert('', 'end', iid=iid, text=v['#0'],
                                         open=True, values=values)

    def add(self):
        n = ItemConfigDialog(self.master, self.fields)
        new = n.result
        if new is None:
            return

        # add_cb should return new iid or None
        iid = self.add_cb(new)

        name = new['#0']
        iid = iid or name

        self.items[iid] = new
        values = [v for k, v in self.items[iid].items() if k != '#0']
        self.tree.insert('', 'end', iid=iid or name, text=name, values=values)

    def remove(self):
        selected = self.tree.selection()[0]

        self.remove_cb(self.items[selected])

        del self.items[selected]

        self.tree.selection_set('')
        self.tree.delete(selected)

    def edit(self, duplicate=False):
        selected = self.tree.selection()[0]
        item = self.items[selected]

        if duplicate:
            item = copy.deepcopy(item)
            item['#0'] = item['#0'] + ' (copy)'

        icd = ItemConfigDialog(self.master, self.fields, item)

        if icd.result is None:
            return

        new_name = icd.result['#0']

        # update list display
        self.items[new_name] = icd.result
        values = [v for k, v in icd.result.items() if k != '#0']

        duped = False

        if new_name != selected:
            if not duplicate:
                self.tree.delete(selected)
            else:
                duped = True

            self.tree.insert('', 'end', iid=new_name, text=new_name,
                             values=values)
        else:
            self.tree.item(selected, text=selected, values=values)

        if duped:
            self.add_cb(icd.result)
        else:
            self.edit_cb(icd.result)

    def duplicate(self):
        self.edit(duplicate=True)

    def selchanged(self, event):
        buts = [b for b in [self.editbut, self.removebut, self.duplicatebut] if b is not None]
        if self.tree.selection():
            for b in buts:
                b.config(state=tk.NORMAL)
        else:
            for b in buts:
                b.config(state=tk.DISABLED)


class List(object):
    def __init__(self, column_defs, rows=[], add_cb=None, remove_cb=None,
                 edit_cb=None):
        self.column_defs = column_defs
        self.rows = rows
        self.add_cb = add_cb
        self.remove_cb = remove_cb
        self.edit_cb = edit_cb

    def get_widget(self, master):
        lm = ListManager(master, self.column_defs, add_cb=self.add_cb,
                         remove_cb=self.remove_cb, edit_cb=self.edit_cb)
        lm.populate(self.rows)

        return lm
