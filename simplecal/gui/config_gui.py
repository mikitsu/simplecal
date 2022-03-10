"""Configuration GUI"""
import tkinter as tk
from tkinter import ttk
import tkinter.simpledialog as tk_dia
import tkinter.filedialog as tk_fdia
import tkinter.colorchooser as tk_cdia
import abc
from .. import config


def validated_entry(master, func, fail_on=ValueError, **kwargs):
    """Add arguments to validate with ``func``

    Default validation arguments are
    ``validate='key'`` and ``validatecommand=(<func>, '%P')``.
    The function is automatically registered.
    To change the ``validatecommand``, pass a tuple without a
    function as first element; it will be inserted.
    Raising ``fail_on`` will fail validation without traceback.
    """
    def wrapper(*args):
        try:
            return func(*args)
        except fail_on:
            return False

    reg = master.register(wrapper)
    if 'validatecommand' in kwargs:
        kwargs['validatecommand'] = (reg, *kwargs['validatecommand'])
    else:
        kwargs['validatecommand'] = (reg, '%P')
    kwargs.setdefault('validate', 'key')
    return ttk.Entry(master, **kwargs)


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


class ConfigBase(abc.ABC):
    @abc.abstractmethod
    def __init__(self, frame, conf):
        pass

    @abc.abstractmethod
    def get_config(self):
        pass

    def labeled_side_input(self, label_text, widget, **kwargs):
        frame = ttk.Frame(self.frame)
        ttk.Label(frame, text=label_text).pack(side=tk.LEFT)
        widget(frame, **kwargs).pack(side=tk.RIGHT)
        return frame


class BasicConfig(ConfigBase):
    def __init__(self, frame, conf):
        self.frame = frame
        dframe = ttk.Frame(frame)
        self.dis_var = tk.StringVar()
        ttk.Label(dframe, text='Display: ').pack(side=tk.LEFT)
        ttk.OptionMenu(
            dframe, self.dis_var, config.get('display'),
            'month', 'vtimeline', 'htimeline', 'vweek', 'hweek',
        ).pack(side=tk.LEFT)
        dframe.pack()
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
            'display': self.dis_var.get(),
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


class AdvancedConfig(ConfigBase):
    def __init__(self, frame, conf):
        self.frame = frame
        self.lum_thres = tk.IntVar(value=conf['lum_threshold'])
        self.labeled_side_input(
            'Luminosity threshold:',
            validated_entry,
            func=(lambda v:  0 <= int(v) <= 255),
            textvariable=self.lum_thres,
        ).pack()
        self.grey_factor = tk.DoubleVar(value=conf['grey_factor'])
        self.labeled_side_input(
            'Grey-out factor:',
            validated_entry,
            func=(lambda v: 0 < float(v) <= 1),
            textvariable=self.grey_factor,
        ).pack()
        self.time_format = tk.StringVar(value=conf['time_format'])
        self.labeled_side_input(
            'Time format:',
            ttk.Entry,
            textvariable=self.time_format,
        ).pack()
        self.pretty_var = tk.BooleanVar(value=conf['save_pretty'])
        f = ttk.Frame(frame)
        ttk.Label(f, text='Pretty-save config:').pack(side=tk.LEFT)
        ttk.Checkbutton(f, variable=self.pretty_var).pack(side=tk.LEFT)
        f.pack()
        ttk.Label(frame, text='Days of week:').pack()
        self.dow = SelectionList(
            frame,
            conf['days_of_week'],
            edit_cb=lambda __: tk_dia.askstring('Day of week', 'Day of week name:'),
            unique=True,
            deletable=False,
        )
        self.wso_index = conf['week_starts_on']
        wframe = ttk.Frame(frame)
        wso = ttk.OptionMenu(
            wframe, tk.StringVar(), *self.dow_with_default(), command=self.update_wso)
        ttk.Label(wframe, text='Week starts on:').pack(side=tk.LEFT)
        wso.pack(side=tk.RIGHT)
        wframe.pack()
        # I hope these are the only ways to select a value.
        for evt in ('<Button>', '<space>'):
            wso.bind(evt, lambda __: wso.set_menu(*self.dow_with_default()))
        ttk.Label(frame, text='Timeline display').pack()
        self.timeline_sels = Selectors((
            IntSelector('past'),
            IntSelector('future'),
            IntSelector('jump'),
        ))
        tframe = ttk.Frame(frame)
        self.timeline_sels.init(tframe, conf['timeline'])
        tframe.pack()

    def get_config(self):
        return {
            'days_of_week': self.dow.items,
            'week_starts_on': self.wso_index,
            'lum_threshold': self.lum_thres.get(),
            'grey_factor': self.grey_factor.get(),
            'time_format': self.time_format.get(),
            'save_pretty': self.pretty_var.get(),
            'timeline': self.timeline_sels.get_conf(),
        }

    def dow_with_default(self):
        dow = self.dow.items
        return dow[self.wso_index], *dow

    def update_wso(self, new_text):
        self.wso_index = self.dow.items.index(new_text)


class Selectors(tuple):
    def init(self, pframe, conf):
        for sel in self:
            frame = ttk.Frame(pframe)
            ttk.Label(frame, text=sel.title).pack(side=tk.LEFT)
            sel.frame = frame
            sel.init(conf)
            frame.pack()

    def get_conf(self):
        return {sel.key: sel.get_conf() for sel in self}


class SelectorBase:
    title_lookup = {}

    def __init__(self, key):
        self.key = key
        self.title = self.title_lookup.get(key, key)


class TextSelector(SelectorBase):
    def init(self, conf):
        self.entry = ttk.Entry(self.frame)
        self.entry.insert('0', conf.get(self.key, ''))
        self.entry.pack(side=tk.LEFT)

    def get_conf(self):
        return self.entry.get() or None


class ColorSelector(SelectorBase):
    title_lookup = {'background': 'background color'}

    def init(self, conf):
        self.button = tk.Button(
            self.frame, bg=conf.get(self.key), command=self.chcolor)
        self.button.pack(side=tk.LEFT)

    def chcolor(self):
        new = tk_cdia.askcolor(self.button['bg'])[1]
        if new is not None:
            self.button['bg'] = new

    def get_conf(self):
        return self.button['bg']


class IntSelector(SelectorBase):
    def init(self, conf):
        var = tk.IntVar(self.frame, conf[self.key])
        validated_entry(self.frame, int, textvariable=var).pack(side=tk.LEFT)
        self.get_conf = var.get


class StyleConfig(ConfigBase):
    items_tmpl = tuple({
        'default': (TextSelector('font'), ColorSelector('background')),
        'dayOfWeek': (TextSelector('font'), ColorSelector('background')),
        'dateNumber': (TextSelector('font'), ColorSelector('background')),
        'eventDisplay': (TextSelector('font'), IntSelector('padx')),
    }.items())

    def __init__(self, frame, conf):
        self.items = [(k, Selectors(v)) for k, v in self.items_tmpl]
        conf = self.orig_conf = conf['styles']
        self.frame = frame

        for name, sels in self.items:
            ttk.Label(frame, text=name).pack()
            cframe = ttk.Frame(frame)
            sels.init(cframe, conf[name])
            cframe.pack()

    def get_config(self):
        return {'styles': {k: sels.get_conf() for k, sels in self.items}}


def display_config_popup(root):
    def save_config():
        conf = config.config.copy()
        for tab in tabs:
            conf.update(tab.get_config())
        assert conf.keys() == config.config.keys()
        config.save(conf)
        toplevel.destroy()

    toplevel = tk.Toplevel(root)
    toplevel.transient(root)
    toplevel.grab_set()
    notebook = ttk.Notebook(toplevel)
    tabs = []
    for cls in ConfigBase.__subclasses__():
        tab = cls(ttk.Frame(notebook), config.config)
        notebook.add(tab.frame, text=cls.__name__.replace('Config', ''))
        tabs.append(tab)
    notebook.pack(fill=tk.X)
    ttk.Button(toplevel, text='Save',  command=save_config).pack(side=tk.LEFT)
    ttk.Button(toplevel, text='Cancel', command=toplevel.destroy).pack(side=tk.RIGHT)
