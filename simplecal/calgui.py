"""iCal GUI"""
import tkinter as tk
from tkinter import ttk
import calendar
import dataclasses
import datetime
import dateutil.tz
from . import callib
from . import config

from .gui.config import display_config_popup

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
