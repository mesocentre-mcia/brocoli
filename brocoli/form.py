from six import print_
from six.moves import tkinter as tk
from six.moves import tkinter_ttk as ttk

import re

class FormField(object):
    def __init__(self, text='', tags=None):
        self.text = text
        self.tags = tags or []

    def from_string(self, s):
        raise NotImplementedError

    def to_string(self):
        raise NotImplementedError

    def get_widget(self, master):
        raise NotImplementedError

    def get_widgets(self, master):
        return tk.Label(master, text=self.text), self.get_widget(master)

    def disables(self):
        return []

    def disables_state(self):
        raise NotImplementedError

class TextField(FormField):
    def __init__(self, text, default_value='', validate_command=None,
                 password_mode=False, tags=None):
        super(TextField, self).__init__(text, tags=tags)

        self.var = tk.StringVar()
        self.var.set(default_value)
        self.validate_command = validate_command
        self.password_mode = password_mode

    def from_string(self, s):
        self.var.set(s)

    def to_string(self):
        return self.var.get()

    def get_widget(self, master):
        show=''
        if self.password_mode:
            show='*'

        entry = tk.Entry(master, textvariable=self.var, show=show)

        if self.validate_command is not None:
            vcmd = (master.register(self.validate_command), '%P')
            entry.config(validate='key', validatecommand=vcmd)

        return entry


class HostnameField(TextField):
    __hostname_re = re.compile('^([_\-\d\w]+(\.)?)*$')

    def __init__(self, text, default_value='', tags=None):
        super(HostnameField, self).__init__(text, default_value, self.validate,
              tags=tags)

    def validate(self, v):
        ok = self.__hostname_re.match(v) != None

        return ok


class PasswordField(TextField):
    def __init__(self, text, encode=lambda s: s, decode=lambda s: s,
                 tags=None):
        super(PasswordField, self).__init__(text, password_mode=True,
                                            tags=tags)

        self.encode = encode
        self.decode = decode

    def from_string(self, s):
        self.var.set(self.decode(s))

    def to_string(self):
        return self.encode(self.var.get())



class IntegerField(TextField):
    def validate(self, v):
        try:
            iv=int(v)
            return True
        except:
            pass

        return False

    def __init__(self, text, default_value=0, tags=None):
        super(IntegerField, self).__init__(text, default_value, self.validate,
                                           tags=tags)


class BooleanField(FormField):
    def __init__(self, text, default_value=False, disables_tags=None,
                 tags=None):
        super(BooleanField, self).__init__(text, tags=tags)

        self.text = text
        self.var = tk.BooleanVar()
        self.var.set(default_value)
        self.disables_tags = disables_tags or []

    def from_string(self, s):
        self.var.set(s)

    def to_string(self):
        return str(self.var.get())

    def get_widget(self, master):
        def changed(*args):
            master.set_disables(self)

        return tk.Checkbutton(master, text=self.text, variable=self.var,
                              onvalue=True, offvalue=False,
                              command=changed)

    def get_widgets(self, master):
        return (self.get_widget(master), )

    def disables(self):
        return self.disables_tags

    def disables_state(self):
        return self.var.get()

class FieldContainer(tk.Frame, object):
    def config(self, **options):
        frame_options = options.copy()

        if 'state' in frame_options:
            v  = frame_options['state']
            del frame_options['state']

            for slave in self.slaves():
                slave.config(state=v)

        tk.Frame.config(self, **frame_options)

class RadioChoiceField(FormField):
    def __init__(self, text, values, default_value = None, vertical=True,
                 tags = None):
        super(RadioChoiceField, self).__init__(text, tags=tags)

        self.values = values
        self.var = tk.StringVar()
        if default_value is None:
            default_value = values[0]

        self.var.set(default_value)

        self.side = tk.TOP
        if not vertical:
            self.side = tk.LEFT

    def from_string(self, s):
        self.var.set(s)

    def to_string(self):
        return self.var.get()

    def get_widget(self, master):
        frame = FieldContainer(master)

        for v in self.values:
            rb = tk.Radiobutton(frame, text=v, value=v, variable=self.var)
            rb.pack(side=self.side)

        return frame


class ComboboxChoiceField(FormField):
    def __init__(self, text, values, default_value=None, tags=None):
        super(ComboboxChoiceField, self).__init__(text, tags=tags)

        self.values = values
        self.var = tk.StringVar()
        if default_value is None:
            default_value = values[0]

        self.var.set(default_value)

    def from_string(self, s):
        self.var.set(s)

    def to_string(self):
        return self.var.get()

    def get_widget(self, master):
        return ttk.Combobox(master, values=self.values, textvariable=self.var)

class FormFrame(tk.Frame, object):
    def __init__(self, master):
        tk.Frame.__init__(self, master)

        self.disablers =  {}
        self.tag_dict = {}

    def grid_fields(self, fieldlist):
        disablers = {}
        tag_dict = {}
        i = 0
        for field in fieldlist:
            tags = field.tags
            disables = field.disables()
            if disables:
                disablers[field] = disables

            widgets = field.get_widgets(self)
            j = 0
            for w in widgets:
                for t in tags:
                    v = tag_dict.get(t, [])
                    v.append(w)
                    tag_dict[t] = v

                w.grid(row=i, column=j)
                j += 1
            i += 1

        self.disablers.update(disablers)
        self.tag_dict.update(tag_dict)

        for disabler in disablers:
            self.set_disables(disabler)

    def set_disables(self, field):
        tags = self.disablers[field]

        state = tk.NORMAL
        if field.disables_state():
            state = tk.DISABLED

        for tag in tags:
            for w in self.tag_dict[tag]:
                w.config(state=state)

if __name__ == '__main__':
    master = tk.Tk()

    hf = HostnameField('host:')

    e = hf.get_widget(master)

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
