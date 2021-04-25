"""iCal GUI"""
import tkinter as tk
from tkinter import ttk
import dataclasses


# TODO: read these setting form config
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
LUM_THRESHOLD = 140
EVENT_PADDING = 10
EVENT_FONT = 'opensans 15'
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
    events: tuple[EventInfo]


class MonthDisplay:
    def __init__(self, master, dates):
        assert not len(dates) % 7
        self.frame = ttk.Frame(master)
        
        for i, day in enumerate(DAYS_OF_WEEK):
            ttk.Label(self.frame, text=day, style='dayOfWeek.TLabel'
                      ).grid(row=0, column=i)
        
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
