import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tk_msg
import datetime
from . import config_gui
from .. import callib


def vcmd_range(low, high):
    return lambda s: not s or s.isdecimal() and low <= int(s) <= high


def hour_entry(parent):
    return ttk.Entry(
        parent,
        width=2,
        validate='key',
        validatecommand=(parent.register(vcmd_range(0, 24)), '%P'),
    )


def minute_entry(parent):
    return ttk.Combobox(
        parent,
        width=2,
        value='00',
        values=('00', '15', '30', '45'),
        validate='key',
        validatecommand=(parent.register(vcmd_range(0, 60)), '%P'),
    )


class EventPopup:
    def __init__(self, root, callback):
        self.callback = callback
        self.se_vars = {}
        self.se_widgets = {}
        self.title_var = tk.StringVar(root)
        self.allday_var = tk.IntVar(root)
        self.end_var = tk.IntVar(root)

        self.toplevel = toplevel = tk.Toplevel(root)
        toplevel.transient(root)
        toplevel.wait_visibility()
        toplevel.grab_set()

        ttk.Label(self.toplevel, textvariable=self.title_var).pack()
        startframe = tk.Frame(self.toplevel)
        ttk.Label(startframe, text='Begins on ').pack(side=tk.LEFT)
        self._build_se_row(startframe, 'start')
        alldaybtn = ttk.Checkbutton(
            toplevel,
            text='All-day event',
            variable=self.allday_var,
            command=self._set_se_entry_states,
        )
        alldaybtn.state(['!alternate', '!selected'])
        alldaybtn.pack()

        endframe = tk.Frame(toplevel)
        endbtn = ttk.Checkbutton(
            endframe,
            text='Ends on ',
            variable=self.end_var,
            command=self._set_se_entry_states,
        )
        endbtn.pack(side=tk.LEFT)
        self._build_se_row(endframe, 'end')
        endbtn.state(['!alternate', 'selected'])
        endbtn.invoke()

        # TODO: rrules

        btnframe = tk.Frame(toplevel)
        ttk.Button(btnframe, text='OK', command=self.on_ok).pack(side=tk.LEFT)
        ttk.Button(btnframe, text='Cancel', command=toplevel.destroy).pack(side=tk.RIGHT)
        btnframe.pack(side=tk.BOTTOM, fill=tk.X, expand=True)

    def _build_se_row(self, frame, key):
        self.se_vars[key, 'day'] = dvar = tk.StringVar(self.toplevel)
        self.se_widgets[key, 'day'] = day = ttk.Entry(
            frame,
            width=10,
            textvariable=dvar,
        )
        self.se_vars[key, 'hours'] = hvar = tk.StringVar(self.toplevel)
        self.se_widgets[key, 'hours'] = hours = ttk.Entry(
            frame,
            width=2,
            textvariable=hvar,
            validate='key',
            validatecommand=(frame.register(vcmd_range(0, 24)), '%P'),
        )
        self.se_vars[key, 'minutes'] = mvar = tk.StringVar(self.toplevel)
        self.se_widgets[key, 'minutes'] = minutes = ttk.Combobox(
            frame,
            width=2,
            value='00',
            values=('00', '15', '30', '45'),
            textvariable=mvar,
            validate='key',
            validatecommand=(frame.register(vcmd_range(0, 60)), '%P'),
        )
        for w in (day, ttk.Label(frame, text=' at '), hours, ttk.Label(frame, text=':'), minutes):
            w.pack(side=tk.LEFT)
        frame.pack()

    def _set_se_entry_states(self):
        sel_time = not self.allday_var.get()
        sel_end = self.end_var.get()
        for (se, dhm), w in self.se_widgets.items():
            cond = (sel_time or dhm == 'day') and (sel_end or se == 'start')
            w.state(['!'*cond + 'disabled'])

    def _get_datetime(self, key):
        vals = {k[1]: v.get() for k, v in self.se_vars if k[0] == key}
        date = datetime.date.fromisoformat(vals['day'])
        if self.allday_var.get():
            time = datetime.time()
        else:
            time = datetime.time(int(vlas['hours']), int(vals['minutes']))
        return datetime.datetime.combine(date, time)

    def on_ok(self):
        # TODO


def add_event(root, calendar, date):
    if calendar is None:
        tk_msg.showerror("Can't write", 'There is no writable calendar')
        return

    popup = EventPopup(root, calendar.add_event)
    popup.title_var.set('New Event')
    popup.se_vars['start', 'day'].set(str(date))
