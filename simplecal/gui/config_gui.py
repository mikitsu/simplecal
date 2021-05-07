"""Configuration GUI"""
import tkinter as tk
from tkinter import ttk
import tkinter.simpledialog as tk_dia
import tkinter.filedialog as tk_fdia
import tkinter.colorchooser as tk_cdia
from .. import config


class SelectionList:
    """Provide a scrollable Listbox that allows adding and deleting entries

    Items may have Listbox.itemconfig-settable data associated with them.
    """
    def __init__(self,
                 master,
                 items,
                 *,
                 new_cb=None,
                 edit_cb=None,
                 unique,  # TODO: set default here when it's clear which is used more often
                 deletable,
                 items_extra=None,
                 ):
        self.frame = ttk.Frame(master)
        self.frame.pack(expand=True, fill=tk.BOTH)
        self.listbox = tk.Listbox(self.frame)
        self.scrollbar = ttk.Scrollbar(self.frame, command=self.listbox.yview)
        self.listbox['yscrollcommand'] = self.scrollbar.set
        self.listbox.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
        self.scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.listbox.insert(0, *items)
        if new_cb is not None:
            self.listbox.insert(0, 'Add new')
        self.listbox.bind('<Double-1>', self.on_select)
        self.listbox.bind('<Delete>', self.on_delete)
        self.new_cb = new_cb
        self.edit_cb = edit_cb
        self.unique = unique
        self.items = list(items)
        self.items_extra = items_extra
        if items_extra is not None:
            for i, extra in enumerate(items_extra, 1):
                self.listbox.itemconfig(i, **extra)

    def on_select(self, event=None):
        lb_index = self.listbox.curselection()[0]
        index = lb_index - (self.new_cb is not None)
        gen_new = index == -1
        if gen_new:
            new = self.new_cb()
        elif self.edit_cb is None:
            return
        elif self.items_extra is None:
            new = self.edit_cb(self.items[index])
        else:
            new = self.edit_cb(self.items[index], self.items_extra[index])
        if new is None:
            return
        if self.items_extra is not None:
            new, extra = new
        if self.unique and self.items.count(new) > 1 - gen_new:
            return  # TODO: error message???
        if gen_new:
            index = len(self.items)
            lb_index = index + 1
        else:
            self.listbox.delete(lb_index)
            self.items.pop(index)
            if self.items_extra is not None:
                self.items_extra.pop(index)
        self.listbox.insert(lb_index, new)
        self.items.insert(index, new)
        if self.items_extra is not None:
            self.listbox.itemconfig(lb_index, **extra)
            self.items_extra.insert(index, extra)

    def on_delete(self, event=None):
        index = (self.listbox.curselection() or [-1])[0]
        if index - (self.new_cb is not None) >= 0:
            self.listbox.delete(index)
            self.items.pop(index - (self.new_cb is not None))
            if self.items_extra is not None:
                self.items_extra.pop(index - (self.new_cb is not None))


class KeyValueSelection:
    def __init__(self, master, name, spec, values):
        self.frame = ttk.Frame(master)
        self.name = name
        self.spec = {k: lambda v: (f(v) if v else f()) for k, f in spec.items()}
        self._values = {}

        footer_frame = ttk.Frame(self.frame)
        ttk.Label(footer_frame, text='new entry:').pack(side=tk.LEFT)
        self.menu = ttk.OptionMenu(
            footer_frame, tk.Variable(), 'select', command=self.add_pair)
        self.menu.pack(side=tk.RIGHT)
        footer_frame.pack(side=tk.BOTOM)

        for k, v in values.items():
            self.add_pair(k, v)

    def add_pair(self, key, value=None):
        def validator(new):
            try:
                self.spec[key](new)
            except ValueError:
                return False
            else:
                return True

        if value is None:
            value = tk_dia.askstring(self.name, key)
            if value is None:
                return
        if not validator(value):
            return

        self._values[key] = var = tk.StringVar(value=value)
        frame = ttk.Frame(self.frame)
        frame.pack(expand=True, fill=tk.X)
        ttk.Label(frame, text=key).pack(side=tk.LEFT)
        ttk.Entry(
            frame, textvariable=var, validate='key',
            validatecommand=(self.frame.register(validator), '%P'),
        ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(
            frame, text='X', width=1,
            command=lambda: (
                frame.destroy(), self._values.pop(key),
                self.menu.set_menu('select', *(self.spec.keys() - self._values.keys())),
            ),
        ).pack(side=tk.LEFT)
        self.menu.set_menu('select', *(self.spec.keys() - self._values.keys()))

    @property
    def values(self):
        return {k: self.spec[k](v.get()) for k, v in self._values.items()}


class BasicConfig:
    def __init__(self, frame, conf):
        self.frame = frame
        ttk.Label(frame, text='Calendars:').pack()
        self.calendars = SelectionList(
            frame,
            conf['calendars'],
            new_cb=self.new_calendar_cb,
            unique=True,
            deletable=True,
        )
        tag_colors = conf['tag_colors'].copy()
        self.default_tag_color_var = tk.StringVar()
        self.default_tag_color_btn = tk.Button(
            frame,
            text='Default tag color',
            bg=tag_colors.pop(''),
            command=self.set_default_tag_color,
        )
        self.default_tag_color_btn.pack()
        self.tags = SelectionList(
            frame,
            tag_colors,
            new_cb=self.new_tag_cb,
            edit_cb=self.edit_tag_cb,
            unique=True,
            deletable=True,
            items_extra=[{'bg': v} for v in tag_colors.values()],
        )

    def get_config(self):
        return {
            'calendars': self.calendars.items,
            'tag_colors': {
                '': self.default_tag_color_btn['bg'],
                **{k: v['bg'] for k, v in zip(self.tags.items, self.tags.items_extra)}
            }
        }

    def new_calendar_cb(self):
        r = tk_fdia.askopenfilename(
            parent=self.frame.winfo_toplevel(),
            filetypes=(('iCalendar', '.ics'), ('All files', '*')),
        )
        return r or None  # empty tuple on cancel, it seems

    def set_default_tag_color(self):
        new = tk_cdia.askcolor(self.default_tag_color_btn['bg'])[1]
        if new is not None:
            self.default_tag_color_btn['bg'] = new

    def new_tag_cb(self):
        # I'm pretty sure the color chooser can't be combined...
        name = tk_dia.askstring('New tag', 'Tag name:')
        if not name:
            return
        color = tk_cdia.askcolor()[1]
        if color is None:
            return
        return name, {'bg': color}

    def edit_tag_cb(self, name, cur_opts):
        color = tk_cdia.askcolor(cur_opts['bg'])[1]
        return None if color is None else (name, {'bg': color})


class AdvancedConfig:
    def __init__(self, frame, conf):
        self.frame = frame
        ttk.Label(frame, text='Days of week:').pack()
        self.dow = SelectionList(
            frame,
            conf['days_of_week'],
            edit_cb=lambda __: tk_dia.askstring('Day of week', 'Day of week name:'),
            unique=True,
            deletable=False,
        )
        self.wso_index = conf['week_starts_on']
        wso = ttk.OptionMenu(
            frame, tk.StringVar(), *self.dow_with_default(), command=self.update_wso)
        ttk.Label(frame, text='Week starts on:').pack(side=tk.LEFT)
        wso.pack(side=tk.RIGHT)
        # I hope these are the only ways to select a value.
        for evt in ('<Button>', '<space>'):
            wso.bind(evt, lambda __: wso.set_menu(*self.dow_with_default()))

    def get_config(self):
        return {
            'days_of_week': self.dow.items,
            'week_starts_on': self.wso_index,
        }

    def dow_with_default(self):
        dow = self.get_config()['days_of_week']
        return dow[self.wso_index], *dow

    def update_wso(self, new_text):
        self.wso_index = self.dow.items.index(new_text)


def display_config_popup(root):
    def save_config():
        # conf = {}
        conf = config.config.copy()
        for tab in tabs:
            conf.update(tab.get_config())
        assert conf.keys() == config.config.keys()
        config.save(conf)
        toplevel.destroy()

    toplevel = tk.Toplevel(root)
    toplevel.transient(root)
    notebook = ttk.Notebook(toplevel)
    tabs = []
    for name, cls in (('Basic', BasicConfig), ('Advanced', AdvancedConfig)):
        tab = cls(ttk.Frame(notebook), config.config)
        notebook.add(tab.frame, text=name)
        tabs.append(tab)
    notebook.pack(fill=tk.X)
    ttk.Button(toplevel, text='Save',  command=save_config).pack(side=tk.LEFT)
    ttk.Button(toplevel, text='Cancel', command=toplevel.destroy).pack(side=tk.RIGHT)
