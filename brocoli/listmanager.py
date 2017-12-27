
from six import print_
from six.moves import tkinter as tk
from six.moves import tkinter_tksimpledialog as tksimpledialog
from six.moves import tkinter_ttk as ttk

import collections
import copy

class ColumnDef(object):
    def __init__(self, name, text, anchor='w', form_field=None):
        self.name = name
        self.text = text
        self.anchor = anchor
        self.form_field = form_field


class ItemConfigDialog(tksimpledialog.Dialog, object):
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

        self.item_frame = form.FormFrame(master)
        self.item_frame.grid_fields(self.item_fields.values(), False)
        self.item_frame.grid(row=0, sticky='nsew')

        self.result = None

    def apply(self):
        self.result = collections.OrderedDict()

        for k, ff in self.item_fields.items():
            self.result[k] = ff.to_string()


class ListManager(tk.Frame):
    def __init__(self, master, columns_def, add=None, remove=None, edit=None):
        tk.Frame.__init__(self, master)

        self.master = master
        self.columns_def = columns_def

        self.fields = collections.OrderedDict([
            (k, cd.form_field) for k, cd in self.columns_def.items()
        ])

        self.items = None

        column_ids = [k for k in self.columns_def.keys() if k != '#0']

        self.tree = ttk.Treeview(self, columns=column_ids,
                                 selectmode='browse')

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

        if add is not None:
            self.newbut = tk.Button(butbox, text='Add', command=self.add)
            self.newbut.grid(row=0, column=0, sticky='ew')

        if remove is not None:
            self.removebut = tk.Button(butbox, text='Remove', command=self.remove,
                                       state=tk.DISABLED)
            self.removebut.grid(row=1, column=0, sticky='ew')

        if edit is not None:
            self.editbut = tk.Button(butbox, text='Edit', command=self.edit,
                                     state=tk.DISABLED)
            self.editbut.grid(row=2, column=0, sticky='ew')

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.grid(sticky='nsew')

        self.tree.bind('<<TreeviewSelect>>', self.selchanged)

    def populate(self, rows):
        for child in self.tree.get_children():
            self.tree.delete(child)

        self.items = collections.OrderedDict([(v['#0'], v) for v in rows])

        for v in rows:
            rows = [v[c] for c in self.columns_def if c != '#0' and c != 'iid']
            iid = v.get('iid', v['#0'])
            root_node = self.tree.insert('', 'end', iid=iid, text=v['#0'],
                                         open=True, values=rows)

    def add(self):
        n = ItemConfigDialog(self.master, self.fields)
        new = n.result
        if new is None:
            return

        name = new['#0']
        self.items[name] = new
        rows = [v for k, v in self.items[name].items() if k != '#0']
        self.tree.insert('', 'end', iid=name, text=name, values=rows)

    def remove(self):
        selected = self.tree.selection()[0]

        del self.items[selected]

        self.tree.selection_set('')
        self.tree.delete(selected)

    def edit(self):
        selected = self.tree.selection()[0]
        item = self.items[selected]

        icd = ItemConfigDialog(self.master, self.fields, item)

        # update list display
        self.items[selected] = icd.result
        rows = [v for k, v in self.items[selected].items() if k != '#0']
        self.tree.item(selected, text=icd.result['#0'], values=rows)

    def selchanged(self, event):
        buts = [b for b in [self.editbut, self.removebut] if b is not None]
        if self.tree.selection():
            for b in buts:
                b.config(state=tk.NORMAL)
        else:
            for b in buts:
                b.config(state=tk.DISABLED)


class List(object):
    def __init__(self, column_defs, rows = []):
        self.column_defs = column_defs
        self.rows = rows

    def get_widget(self, master):
        lm = ListManager(master, self.column_defs)
        lm.populate(self.rows)

        return lm


if __name__ == '__main__':
    import form

    root = tk.Tk()

    columns_def = collections.OrderedDict([
        ('#0', ColumnDef('#0', 'name', form_field=form.TextField('name:'))),
        ('col1', ColumnDef('col1', 'column 1', form_field=form.TextField('column 1 text:'))),
        ('col2', ColumnDef('col2', 'column 2', form_field=form.IntegerField('column 2 integer:'))),
    ])

    lm = ListManager(root, columns_def, add=True, remove=True,
                     edit=True)

    rows = [
        {'#0': 'value 1', 'col1': 'v1c1', 'col2': 1},
        {'#0': 'value 2', 'col1': 'v2c1', 'col2': 2},
    ]

    lm.populate(rows)




    root.mainloop()
