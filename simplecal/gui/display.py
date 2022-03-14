"""display a calendar"""
import tkinter as tk
from tkinter import ttk
import dataclasses
import calendar
import datetime
import dateutil.tz
from .. import callib
from .. import config


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
    weekday: str
    grey_out: bool
    date: datetime.date
    events: list[EventInfo] = dataclasses.field(default_factory=list)


class DisplayBase:
    def __init__(self, parent, events, add_event):
        self.frame = ttk.Frame(parent)
        self.events = events
        self.add_event_cb = add_event
        self.cur_day = None

    def move(self, offset):
        self.display(self._move(offset))

    def display(self, day):
        self.cur_day = day
        kill_all_children(self.frame)
        self._display()


class MonthDisplay(DisplayBase):
    def _move(self, offset):
        dyear, tmonth = divmod(self.cur_day.month + offset - 1, 12)
        return self.cur_day.replace(
            year=self.cur_day.year + dyear,
            month=tmonth + 1,
        )

    def get_dateinfos(self):
        year, month = self.cur_day.year, self.cur_day.month
        first_wd, last_d = calendar.monthrange(year, month)
        extra_before = (first_wd - config.get('week_starts_on')) % 7
        return generate_dateinfos(
            self.events,
            datetime.date(year, month, 1),
            datetime.date(year, month, last_d),
            extra_before,
            -(last_d + extra_before) % 7,
        )

    def _display(self):
        for i, day in enumerate(config.get('days_of_week'), -config.get('week_starts_on')):
            ttk.Label(self.frame, text=day, style='dayOfWeek.TLabel'
                      ).grid(row=0, column=i%7)
            self.frame.grid_columnconfigure(i%7, weight=1)
    
        for i, date in enumerate(self.get_dateinfos(), 7):
            self.display_date(date, *divmod(i, 7))
            if i % 7 == 0:
                self.frame.grid_rowconfigure(i//7, weight=1)

    def display_date(self, date, row, col):
        st = get_style_helper(date)
        cell_frame = ttk.Frame(self.frame, style=st('dateCell.TFrame'))
        cell_frame.grid(row=row, column=col, sticky=tk.NSEW)
        ttk.Label(cell_frame, text=date.number, style=st('dateNumber.TLabel')
                  ).pack(anchor=tk.NW)
        make_event_frame(cell_frame, date)
        if self.add_event_cb is not None:
            cell_frame.bind('<1>', lambda e: self.add_event_cb(date.date))


class TimelineDisplay(DisplayBase):
    move_unit = config.get('timeline', 'jump')
    vertical: bool

    def _move(self, offset):
        return self.cur_day + deltadays(offset*self.move_unit)

    def get_dateinfos(self):
        return generate_dateinfos(
            self.events,
            self.cur_day,
            self.cur_day + deltadays(config.get('timeline', 'future')),
            config.get('timeline', 'past'),
        )

    def _display(self):
        for date in self.get_dateinfos():
            st = get_style_helper(date)
            frame = self.add_frame(st('dateCell.TFrame'))
            hframe = ttk.Frame(frame, style=st('dateCell.TFrame'))
            ttk.Label(
                hframe, text=date.number, style=st('dateNumber.TLabel')
            ).pack(side=tk.LEFT)
            ttk.Label(
                hframe, text=date.weekday, style=st('dayOfWeek.TLabel')
            ).pack(side=tk.RIGHT)
            hframe.pack(fill=tk.X, expand=True)
            make_event_frame(frame, date)

    def add_frame(self, style):
        frame = ttk.Frame(self.frame, style=style)
        side = tk.TOP if self.vertical else tk.LEFT
        frame.pack(side=side, expand=True, fill=tk.X)
        return frame


class WeekDisplay(TimelineDisplay):
    move_unit = 7

    def get_dateinfos(self):
        start = self.cur_day - deltadays(
            (self.cur_day.weekday()-config.get('week_starts_on')) % 7)
        return generate_dateinfos(self.events, start, start + deltadays(6))


def make_event_frame(parent, date):
    st = get_style_helper(date)
    event_frame = ttk.Frame(parent, style=st('dateCell.TFrame'))
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


def get_style_helper(date):
    return lambda name: ('grey.' if date.grey_out else '') + name


def kill_all_children(widget):
    for child in tuple(widget.children.values()):
        child.destroy()


def deltadays(days):
    return datetime.timedelta(days=days)


def date_range(start, end):
    return map(datetime.date.fromordinal, range(start.toordinal(), 1+end.toordinal()))


def generate_dateinfos(events, start, end, extra_before=0, extra_after=0):
    d1 = deltadays(1)
    start_ = start - deltadays(extra_before)
    end_  = end + deltadays(extra_after)
    dates = {
        d: DateInfo(
            d.toordinal(),
            str(d.day),
            config.get('days_of_week')[d.weekday()],
            not (start <= d <= end),
            d,
        ) for d in date_range(start_, end_)
    }

    # one day safety for timezones quirks (which probably won't actually happen)
    q_start = datetime.datetime.combine((start_ - d1), datetime.time.min)\
              .replace(tzinfo=dateutil.tz.UTC)
    q_end = datetime.datetime.combine((end_ + d1), datetime.time.max)\
            .replace(tzinfo=dateutil.tz.UTC)
    time_format = config.get('time_format')
    colors = config.get('tag_colors')
    for evt in callib.filter_events(events, q_start, q_end):
        info = EventInfo(
            times=(evt.start, -evt.end.timestamp()),
            summary=evt.summary,
            time='All day' if evt.all_day else evt.start.strftime(time_format),
            color=hex(hash(next((c for c in evt.categories if c in colors), ''))),
        )
        for d in date_range(evt.start, evt.end - datetime.timedelta.resolution):
            try:
                dates[d].events.append(info)
            except KeyError:
                pass

    for date_info in dates.values():
        date_info.events.sort(key=lambda e: e.times)

    return tuple(dates.values())
