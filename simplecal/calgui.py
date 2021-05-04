"""iCal GUI"""
import tkinter as tk
from tkinter import ttk
import tkinter.simpledialog as tk_dia
import tkinter.filedialog as tk_fdia
import calendar
import dataclasses
import datetime
import dateutil.tz
from . import callib
from . import config


@dataclasses.dataclass
class EventInfo:
    times: tuple[int, int]
    summary: str
    time: str
    color: str  # hex(hash(tag name or ''))


@dataclasses.dataclass
class DateInfo:
    id: int
    number: str
    grey_out: bool
    events: list[EventInfo] = dataclasses.field(default_factory=list)


class MonthDisplay:
    def __init__(self, master, dates):
        assert not len(dates) % 7
        self.frame = ttk.Frame(master)

        for i, day in enumerate(config.get('days_of_week'), -config.get('week_starts_on')):
            ttk.Label(self.frame, text=day, style='dayOfWeek.TLabel'
                      ).grid(row=0, column=i%7)
            self.frame.grid_columnconfigure(i%7, weight=1)

        self.cell_frames = {}
        for i, date in enumerate(dates, 7):
            self.cell_frames[date.id] = (tk.Frame(self.frame), *divmod(i, 7))
            self.display_date(date)
            if i % 7 == 0:
                self.frame.grid_rowconfigure(i//7, weight=1)

    def display_date(self, date):
        def st(name):
            return ('grey.' if date.grey_out else '') + name
        old_frame, r, c = self.cell_frames[date.id]
        cell_frame = ttk.Frame(old_frame.master, style=st('dateCell.TFrame'))
        old_frame.destroy()
        self.cell_frames[date.id] = cell_frame, r, c
        cell_frame.grid(row=r, column=c, sticky=tk.NSEW)
        del old_frame, c, r

        ttk.Label(cell_frame, text=date.number, style=st('dateNumber.TLabel')
                  ).pack(anchor=tk.NW)
        event_frame = ttk.Frame(cell_frame, style=st('dateCell.TFrame'))
        for evt in date.events:
            conf_padx = config.get('styles', 'eventDisplay', 'padx')
            if isinstance(conf_padx, int):
                conf_padx = (conf_padx, conf_padx)
            padx = [c*(t == date.id) for c, t in zip(conf_padx, evt.times)]

            st_pre = st(f'{evt.color}.eventDisplay.')
            f = ttk.Frame(event_frame, style=st_pre+'TFrame')
            ttk.Label(f, text=evt.summary, style=st_pre+'TLabel').pack(side=tk.LEFT)
            ttk.Label(f, text=evt.time, style=st_pre+'TLabel').pack(side=tk.RIGHT)
            f.pack(expand=True, fill=tk.X, padx=padx)
        event_frame.pack(expand=True, fill=tk.X, anchor=tk.N)


def generate_dateinfos(year, month, events):
    d1 = datetime.timedelta(days=1)
    first_wd, last_d = calendar.monthrange(year, month)

    extra_before = (first_wd - config.get('week_starts_on')) % 7
    extra_after = -(last_d + extra_before) % 7
    start = datetime.date(year, month, 1) - datetime.timedelta(days=extra_before)
    end = datetime.date(year, month, last_d) + datetime.timedelta(days=extra_after)

    dates = {}
    cur = start
    while cur <= end:
        dates[cur] = DateInfo(cur.toordinal(), str(cur.day), cur.month != month)
        cur += d1

    # one day safety for timezones quirks (which probably won't actually happen)
    q_start = datetime.datetime.combine((start - d1), datetime.time.min)\
              .replace(tzinfo=dateutil.tz.UTC)
    q_end = datetime.datetime.combine((end + d1), datetime.time.max)\
            .replace(tzinfo=dateutil.tz.UTC)
    time_format = config.get('time_format')
    colors = config.get('tag_colors')
    for evt in callib.filter_events(events, q_start, q_end):
        info = EventInfo(
            times=(evt.start.toordinal(), evt.end.toordinal()),
            summary=evt.summary,
            time='All day' if evt.all_day else evt.start.strftime(time_format),
            color=hex(hash(next((c for c in evt.categories if c in colors), ''))),
        )
        for date_ord in range(evt.start.toordinal(), evt.end.toordinal()+1):
            try:
                dates[datetime.date.fromordinal(date_ord)].events.append(info)
            except KeyError:
                pass

    for date_info in dates.values():
        date_info.events.sort(key=lambda e: e.times)

    return tuple(dates.values())


def apply_styles(widget):
    STYLE_CLASSES = (
        ('default', '.'),
        ('dayOfWeek', 'dayOfWeek.TLabel'),
        ('dateNumber', 'dateNumber.TLabel'),
        ('dateCell', 'dateCell.TFrame'),
    )
    def conf_grey(name):
        opts = {pre + 'ground': style.lookup(name, pre + 'ground') for pre in ('fore', 'back')}
        opts = {k: '#' + ''.join(  # hex -> RGB -> *factor -> hex for fore+back
            format(round(int(v[i:i+2], 16) * config.get('grey_factor')), '0>2x')
            for i in range(1, 7)) for k, v in opts.items()}
        style.configure('grey.' + name, **opts)

    style = ttk.Style(widget)
    for conf_name, style_name in STYLE_CLASSES:
        style.configure(style_name, **config.get('styles', conf_name))
    conf_grey('dateNumber.TLabel')
    conf_grey('dateCell.TFrame')

    for tag, color in config.get('tag_colors').items():
        name = hex(hash(tag)) + '.eventDisplay.'
        assert color.startswith('#') and len(color) == 7
        for suff in ('TFrame', 'TLabel'):
            col_rgb = [int(color[i:i+2], 16) for i in range(1, 7)]
            # formula from https://stackoverflow.com/a/3943023
            lum = col_rgb[0]*0.299 + col_rgb[1]*0.587 + col_rgb[2]*0.114
            fg = '#000000' if lum < config.get('lum_threshold') else '#ffffff'
            opts = {'background': color, 'foreground': fg}
            style.configure(name + suff, **opts)
            conf_grey(name + suff)


class SelectionList:
    """Provide a scrollable Listbox that allows adding and deleting entries

    Items may have Listbox.itemconfig-settable data associated with them.
    """
    def __init__(self,
                 master,
                 items,
                 new_cb=None,
                 edit_cb=None,
                 unique=False,
                 deletable=False,
                 items_extra=None,
                 ):
        self.frame = ttk.Frame(master)
        self.frame.pack()
        self.listbox = tk.Listbox(self.frame)
        self.scrollbar = ttk.Scrollbar(self.frame, command=self.listbox.yview)
        self.listbox['yscrollcommand'] = self.scrollbar.set
        self.listbox.pack(side=tk.LEFT)
        self.scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.listbox.insert(0, *items)
        if new_cb is not None:
            self.listbox.insert(0, 'Add new')
        self.listbox.bind('<Double-1>', self.on_select)
        self.listbox.bind('<Delete>', self.on_delete)
        self.new_cb = new_cb
        self.edit_cb = edit_cb
        self.unique = unique
        self.items = items
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
        index = self.listbox.curselection()[0]
        if index != 0 or self.new_cb is None:
            self.listbox.delete(index)
            self.items.pop(index-1)
            if self.items_extra is not None:
                self.items_extra.pop(index-1)


def display_config_popup(root):
    conf = config.config
    toplevel = tk.Toplevel(root)
    toplevel.transient(root)
    tabs = ttk.Notebook(toplevel)
    tab_basic = ttk.Frame(tabs)
    ttk.Label(tab_basic, text='Calendars:').pack()
    SelectionList(
        tab_basic,
        conf['calendars'],  # mutated
        lambda: tk_fdia.askopenfilename(
            parent=toplevel, filetypes=(('iCalendar', '.ics'), ('All files', '*'))),
        unique=True,
    )
    ttk.Label(tab_basic, text='Days of week:').pack()
    SelectionList(
        tab_basic,
        conf['days_of_week'],  # mutated
        edit_cb=lambda __: tk_dia.askstring('Day of week', 'Day of week name:'),
        deletable=False,
    )
    wso_var = tk.StringVar()
    wso = ttk.OptionMenu(tab_basic, wso_var, conf['days_of_week'][0], *conf['days_of_week'])
    ttk.Label(tab_basic, text='Week starts on:').pack(side=tk.LEFT)
    wso.pack(side=tk.RIGHT)
    # I hope these are the only ways to select a value.
    for evt in ('<Button>', '<space>'):
        wso.bind(evt, lambda __: wso.set_menu(
            conf['days_of_week'][0], *conf['days_of_week']))
    tabs.add(tab_basic, text='Basic')
    tabs.pack(fill=tk.X)
    ttk.Button(toplevel, text='Save',
               command=lambda: (toplevel.destroy(), config.save(
                   {**conf, 'week_starts_on': conf['days_of_week'].index(wso_var.get())})),
               ).pack(side=tk.LEFT)
    ttk.Button(toplevel, text='Cancel', command=toplevel.destroy).pack(side=tk.RIGHT)


def run_app(year, month):
    root = tk.Tk()
    root.bind('<c>', lambda e: display_config_popup(root))  # TEMP for testing
    apply_styles(root)
    # TODO: as soon as there are a bit more features,
    # move the calendar to a separate file
    events = []
    for cal in config.get('calendars'):
        try:
            with open(cal) as f:
                data = f.read()
        except OSError:
            continue
        events += callib.get_events(data)
    dates = generate_dateinfos(year, month, events)
    md = MonthDisplay(root, dates)
    md.frame.pack(expand=True, fill=tk.BOTH)
    root.mainloop()
