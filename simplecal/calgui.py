"""iCal GUI"""
import tkinter as tk
from tkinter import ttk
import calendar
import dataclasses
import datetime
import dateutil.tz
from . import callib


# TODO: read these settings form config
DAYS_OF_WEEK = calendar.day_abbr
WEEK_STARTS_ON = 0
TIME_FORMAT = '%H:%M'
LUM_THRESHOLD = 140
EVENT_PADDING = 10
EVENT_FONT = 'opensans 15'
COLORS = {
    'MyTag': (255, 255, 0),
}
DEFAULT_COLOR = (100, 100, 50)
ttk.Style().configure(
    '.',
    foreground='white',
    background='#444444',
)
ttk.Style().configure(
    'dayOfWeek.TLabel',
    font='opensans 30',
    padding=20,
)
ttk.Style().configure(
    'dateNumber.TLabel',
    font='opensans 25',
)
ttk.Style().configure(
    'dateCell.TFrame',
    borderwidth=10,
)


@dataclasses.dataclass
class EventInfo:
    times: tuple[int, int]
    summary: str
    time: str
    color: tuple[int, int, int]


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
        
        for i, day in enumerate(DAYS_OF_WEEK):
            ttk.Label(self.frame, text=day, style='dayOfWeek.TLabel'
                      ).grid(row=0, column=i)
            self.frame.grid_columnconfigure(i, weight=1)

        self.cell_frames = {}
        for i, date in enumerate(dates, 7):
            self.cell_frames[date.id] = (tk.Frame(self.frame), *divmod(i, 7))
            self.display_date(date)

    def display_date(self, date):
        old_frame, r, c = self.cell_frames[date.id]
        cell_frame = ttk.Frame(old_frame.master, style='dateCell.TFrame')
        old_frame.destroy()
        self.cell_frames[date.id] = cell_frame
        cell_frame.grid(row=r, column=c, sticky=tk.NSEW)
        del old_frame, c, r

        ttk.Label(cell_frame, text=date.number, style='dateNumber.TLabel'
                  ).pack(anchor=tk.NW)
        for evt in date.events:
            # formula from https://stackoverflow.com/a/3943023
            lum = evt.color[0]*0.299 + evt.color[1]*0.587 + evt.color[2]*0.114
            if lum > LUM_THRESHOLD:
                fg = 'black'
            else:
                fg = 'white'
            bg = '#' + ''.join(format(v, '0>2x') for v in evt.color)
            padx = [EVENT_PADDING*(t == date.id) for t in evt.times]
            opts = {'fg': fg, 'bg': bg, 'font': EVENT_FONT}

            f = tk.Frame(cell_frame, bg=bg)
            tk.Label(f, text=evt.summary, **opts).pack(side=tk.LEFT)
            tk.Label(f, text=evt.time, **opts).pack(side=tk.RIGHT)
            f.pack(expand=True, fill=tk.X, padx=padx, pady=(EVENT_PADDING, 0), anchor=tk.N)


def generate_dateinfos(year, month, events):
    d1 = datetime.timedelta(days=1)
    first_wd, last_d = calendar.monthrange(year, month)

    extra_before = (first_wd - WEEK_STARTS_ON) % 7
    extra_after = (6-WEEK_STARTS_ON - calendar.weekday(year, month, last_d)) % 7
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
    for evt in callib.filter_events(events, q_start, q_end):
        info = EventInfo(
            times=(evt.start.toordinal(), evt.end.toordinal()),
            summary=evt.summary,
            time='All day' if evt.all_day else evt.start.strftime(TIME_FORMAT),
            color=next((COLORS[c] for c in evt.categories if c in COLORS), DEFAULT_COLOR),
        )
        for date_ord in range(evt.start.toordinal(), evt.end.toordinal()+1):
            try:
                dates[datetime.date.fromordinal(date_ord)].events.append(info)
            except KeyError:
                pass

    for date_info in dates.values():
        date_info.events.sort(key=lambda e: e.times)

    return tuple(dates.values())
