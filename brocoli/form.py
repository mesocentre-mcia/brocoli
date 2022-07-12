from six import print_
from six.moves import tkinter as tk
from six.moves import tkinter_ttk as ttk
from six.moves import tkinter_tkfiledialog as filedialog

import re

"""
Defines helper classes to build forms
"""


class FormField(object):
    """
    Base class for form fields objects. Most methods should be overridden.
    """
    def __init__(self, text='', tags=None):
        """
        Constructor
        """
        self.text = text
        self.tags = tags or []

    def reset(self):
        '''
        Resets internal formField state
        '''
        raise NotImplementedError

    def from_string(self, s):
        """
        Sets field value from argument string
        """
        raise NotImplementedError

    def contents_from_config(self, config):
        pass

    def to_string(self):
        """
        Translates field value to string
        """
        raise NotImplementedError

    def get_contents(self):
        return {}

    def get_widget(self, master):
        """
        Creates a new "entry" widget
        """
        raise NotImplementedError

    def get_widgets(self, master):
        """
        Returns a pair consisting of a label and an "entry" widget
        """
        return (tk.Label(master, text=self.text, anchor='e'),
                self.get_widget(master))

    def disables(self):
        """
        Returns a list of tags that are "disabled" by the current FormField
        """
        return []

    def enables(self):
        """
        Returns a list of tags that are "enabled" by the current FormField
        """
        return []


class TextField(FormField):
    """
    A FormField holding a text (a tk.Entry)
    """
    def __init__(self, text, default_value='', validate_command=None,
                 password_mode=False, tags=None):
        super(TextField, self).__init__(text, tags=tags)

        self.var = tk.StringVar()
        self.default_value = default_value
        self.reset()
        self.validate_command = validate_command
        self.password_mode = password_mode

    def reset(self):
        self.var.set(self.default_value)

    def from_string(self, s):
        self.var.set(s)

    def to_string(self):
        return self.var.get()

    def get_widget(self, master):
        show = ''
        if self.password_mode:
            show = '*'

        entry = tk.Entry(master, textvariable=self.var, show=show)

        if self.validate_command is not None:
            vcmd = (master.register(self.validate_command), '%P')
            entry.config(validate='key', validatecommand=vcmd)

        return entry


class HostnameField(TextField):
    """
    A TextField accepting host names only
    """
    __hostname_re = re.compile('^[_\-\d\w\.]+$')

    def __init__(self, text, default_value='', tags=None):
        super(HostnameField, self).__init__(text, default_value, self.validate,
                                            tags=tags)

    def validate(self, v):
        ok = self.__hostname_re.match(v) is not None

        return ok


class PasswordField(TextField):
    """
    A TextField for a password. The tk.Entry displays stars instead of the
    current text value
    """
    def __init__(self, text, encode=lambda s: s, decode=lambda s: s,
                 return_cb=None, tags=None):
        super(PasswordField, self).__init__(text, password_mode=True,
                                            tags=tags)

        self.encode = encode
        self.decode = decode
        self.return_cb = return_cb

    def from_string(self, s):
        self.var.set(self.decode(s))

    def to_string(self):
        return self.encode(self.var.get())

    def get_widget(self, master):
        entry = super(PasswordField, self).get_widget(master)

        if self.return_cb is not None:
            entry.bind('<Return>', lambda e: self.return_cb())

        return entry


class IntegerField(TextField):
    """
    A TextField accepting only integer litterals
    """
    def validate(self, v):
        try:
            iv = int(v)
            return True
        except:
            pass

        return False

    def __init__(self, text, default_value=0, tags=None):
        super(IntegerField, self).__init__(text, default_value, self.validate,
                                           tags=tags)


class BooleanField(FormField):
    """
    A FormField holding a bool, manifested by a tk.Checkbutton
    """
    def __init__(self, text, default_value=False, state_change_cb=None,
                 disables_tags=None, enables_tags=None, tags=None):
        super(BooleanField, self).__init__(text, tags=tags)

        self.text = text
        self.var = tk.BooleanVar()
        self.default_value = default_value
        self.state_change_cb = state_change_cb
        self.reset()
        self.disables_tags = disables_tags or []
        self.enables_tags = enables_tags or []

    def reset(self):
        self.var.set(self.default_value)

    def from_string(self, s):
        self.var.set(s)

    def to_string(self):
        return str(self.var.get())

    def get_widget(self, master):
        def changed(*args):
            if self.state_change_cb is not None:
                self.state_change_cb(self.var.get())

            master.disenables_changed(self)

        return tk.Checkbutton(master, variable=self.var,
                              onvalue=True, offvalue=False,
                              command=changed, anchor='w')

    def disables(self):
        return self.disables_tags

    def enables(self):
        return self.enables_tags

    def disables_state(self):
        if self.var.get():
            return tk.DISABLED

        return tk.NORMAL

    def enables_state(self):
        if self.var.get():
            return tk.NORMAL

        return tk.DISABLED


class FieldContainer(tk.Frame, object):
    """
    A tk.Frame sub-class specialized to propagate state changes to its children
    """
    def config(self, **options):
        frame_options = options.copy()

        if 'state' in frame_options:
            v = frame_options['state']
            del frame_options['state']

            for slave in (self.pack_slaves() + self.grid_slaves() +
                          self.place_slaves()):
                slave.config(state=v)

        tk.Frame.config(self, **frame_options)


class RadioChoiceField(FormField):
    """
    A FormField allowing to choose between several fixed values, manifested by
    tk.Radiobuttons
    """
    def __init__(self, text, values, default_value=None, vertical=True,
                 tags=None):
        super(RadioChoiceField, self).__init__(text, tags=tags)

        self.values = values
        self.var = tk.StringVar()
        if default_value is None:
            default_value = values[0]

        self.default_value = default_value
        self.reset()

        self.side = tk.TOP
        if not vertical:
            self.side = tk.LEFT

    def reset(self):
        self.var.set(self.default_value)

    def from_string(self, s):
        self.var.set(s)

    def to_string(self):
        return self.var.get()

    def get_widget(self, master):
        frame = FieldContainer(master)
        frame.configure(relief=tk.GROOVE, borderwidth=2)

        inner_frame = FieldContainer(frame)
        inner_frame.pack()

        for v in self.values:
            rb = tk.Radiobutton(inner_frame, text=v, value=v, variable=self.var)
            rb.pack(side=self.side, anchor=tk.NW)

        return frame


class ComboboxChoiceField(FormField):
    """
    A FormField allowing to choose between several fixed values, manifested by
    a ttk.Combobox
    """
    def __init__(self, text, values, default_value=None, tags=None):
        super(ComboboxChoiceField, self).__init__(text, tags=tags)

        self.values = list(values)
        self.var = tk.StringVar()
        if default_value is None:
            default_value = self.values[0]

        self.default_value = default_value
        self.reset()

    def reset(self):
        self.var.set(self.default_value)

    def from_string(self, s):
        self.var.set(s)

    def to_string(self):
        return self.var.get()

    def get_widget(self, master):
        return ttk.Combobox(master, values=self.values, textvariable=self.var)


class FileSelectorField(TextField):
    """
    A FormField allowing to choose a local file
    """
    def __init__(self, text, default_value='',
                 tags=None):
        super(FileSelectorField, self).__init__(text, default_value, tags=tags)

    def get_widget(self, master):
        frame = FieldContainer(master)

        entry = tk.Entry(frame, textvariable=self.var)
        entry.grid(row=0, column=0, sticky='ew')
        but = tk.Button(frame, text='browse', command=self.command)
        but.grid(row=0, column=1)

        frame.columnconfigure(0, weight=1)

        return frame

    def command(self):
        file = filedialog.askopenfilename()

        if file is None:
            return

        self.var.set(file)


class FormFrame(tk.Frame, object):
    """
    A tk.Frame fr holding a form (i.e. a list of FormField generated widget
    pairs)
    """
    class TagTargets(list):
        def __init__(self):
            self.state = tk.DISABLED

    def __init__(self, master):
        tk.Frame.__init__(self, master)

        self.disablers = {}
        self.enablers = {}
        self.tag_dict = {}

    def grid_fields(self, fieldlist, focus_first=True):
        disablers = {}
        enablers = {}
        tag_dict = {}
        i = 0
        for field in fieldlist:
            tags = field.tags
            disables = field.disables()
            if disables:
                disablers[field] = disables
            enables = field.enables()
            if enables:
                enablers[field] = enables

            widgets = field.get_widgets(self)
            j = 0
            for w in widgets:
                for t in tags:
                    v = tag_dict.get(t, self.TagTargets())
                    v.append(w)
                    tag_dict[t] = v

                w.grid(row=i, column=j, sticky='ew')
                j += 1
            if i == 0 and focus_first:
                widgets[-1].focus_set()
            i += 1

        self.disablers.update(disablers)
        self.enablers.update(enablers)
        self.tag_dict.update(tag_dict)

        for disabler in disablers:
            self.set_disables(disabler)

        for enabler in enablers:
            self.set_enables(enabler)

    def ungrid_fields(self):
        for s in self.grid_slaves():
            s.grid_remove()

    def set_disables(self, field):
        tags = self.disablers[field]

        state = field.disables_state()

        for tag in tags:
            tag_targets = self.tag_dict.get(tag, self.TagTargets())
            tag_targets.state = state
            for w in tag_targets:
                state = tk.NORMAL
                for tt in self.tag_dict.values():
                    if tt.state == tk.DISABLED and w in tt:
                        state = tk.DISABLED
                    w.config(state=state)

    def set_enables(self, field):
        tags = self.enablers[field]

        state = field.enables_state()

        for tag in tags:
            tag_targets = self.tag_dict.get(tag, self.TagTargets())
            tag_targets.state = state
            for w in tag_targets:
                state = tk.NORMAL
                for tt in self.tag_dict.values():
                    if tt.state == tk.DISABLED and w in tt:
                        state = tk.DISABLED
                    w.config(state=state)

    def disenables_changed(self, field):
        if field in self.enablers:
            self.set_enables(field)
        if field in self.disablers:
            self.set_disables(field)


class CboxSubForm(ComboboxChoiceField):
    def __init__(self, text, item_dict, default_value=None, tags=None):
        super(CboxSubForm, self).__init__(text, item_dict.keys(),
                                          default_value, tags=tags)

        self.item_dict = item_dict

    def get_widget(self, master):
        frame = FieldContainer(master)

        cbox = ttk.Combobox(frame, values=self.values, textvariable=self.var)
        cbox.grid(row=0, column=0, sticky='ew')

        ff = FormFrame(frame)
        ff.grid(row=1, column=0, sticky='ew')

        def changed(event=None):
            item = cbox.get()
            config_fields = self.item_dict[item]

            ff.ungrid_fields()

            ff.grid_fields(config_fields.values(), False)

        changed()
        cbox.bind('<<ComboboxSelected>>', changed)

        frame.columnconfigure(0, weight=1)

        return frame

    def contents_from_config(self, config):
        choice = self.var.get()

        for key, field in self.item_dict[choice].items():
            field.from_string(config[key])
            field.contents_from_config(config)

    def get_contents(self):
        ret = {}

        choice = self.var.get()

        for key, field in self.item_dict[choice].items():
            ret[key] = field.to_string()
            ret.update(field.get_contents())

        return ret


class FrameGenerator(object):
    def __init__(self, fields):
        self.fields = fields

    def get_widget(self, master):
        ff = FormFrame(master)

        ff.grid_fields(self.fields)

        return ff

if __name__ == '__main__':
    master = tk.Tk()

    hf = HostnameField('host:')

    bf = BooleanField('toto', disables_tags=['toto'])

    pf = PasswordField('pwd:', tags=['toto'])

    if_ = IntegerField('integer:', 12, tags=['toto'])

    rbc = RadioChoiceField('radiochoice:', ['one', 'two', 'three'],
                           vertical=False, tags=['toto'])

    cbcf = ComboboxChoiceField('comboboxchoice:', ['yi', 'er', 'san'],
                               tags=['toto'])

    ff = FormFrame(master)
    ff.grid_fields([hf, bf, pf, if_, rbc, cbcf])
    ff.pack()
    master.mainloop()
