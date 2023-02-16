import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tk_msg
import datetime
import dataclasses
from functools import partial
import logging
import uuid
from .. import config
from .. import callib


def vcmd_range(low, high):
    return lambda s: not s or s.isdecimal() and low <= int(s) < high


class DatetimeInput:
    def __init__(self, frame, ntime_state_var, gen_state_vars):
        self.state_vars = gen_state_vars
        self.ntime_state_var = ntime_state_var
        for var in gen_state_vars:
            var.trace_add('write', lambda *_: self.update_state())
        ntime_state_var.trace_add('write', lambda *_: self.update_state())

        self.dvar = tk.StringVar(frame)
        self.day = ttk.Entry(
            frame,
            width=10,
            textvariable=self.dvar,
        )
        self.hvar = tk.StringVar(frame)
        self.hour = ttk.Entry(
            frame,
            width=2,
            textvariable=self.hvar,
            validate='key',
            validatecommand=(frame.register(vcmd_range(0, 24)), '%P'),
        )
        self.mvar = tk.StringVar(frame)
        self.minute = ttk.Combobox(
            frame,
            width=2,
            value='00',
            values=('00', '15', '30', '45'),
            textvariable=self.mvar,
            validate='key',
            validatecommand=(frame.register(vcmd_range(0, 60)), '%P'),
        )
        for w in (self.day, ttk.Label(frame, text=' at '), self.hour,
                  ttk.Label(frame, text=':'), self.minute):
            w.pack(side=tk.LEFT)
        frame.pack()

    def set(self, value):
        if isinstance(value, datetime.datetime):
            self.hvar.set(str(value.hour))
            self.mvar.set(str(value.minute))
            value = value.date()
        self.dvar.set(str(value))

    def get(self):
        if not all(var.get() for var in self.state_vars):
            return None
        date = datetime.date.fromisoformat(self.dvar.get())
        if self.ntime_state_var.get():
            return date
        else:
            time = datetime.time(int(self.hvar.get()), int(self.mvar.get()))
            return datetime.datetime.combine(date, time)

    def update_state(self):
        state_all = all(var.get() for var in self.state_vars)
        state_time = not self.ntime_state_var.get()
        self.day.state(['!'*state_all + 'disabled'])
        for w in (self.hour, self.minute):
            w.state(['!'*(state_time and state_all) + 'disabled'])


class RRuleInput:
    def __init__(self, frame, start, time_var):
        self.frame = frame
        self.repeat_var = tk.IntVar(frame, 0)
        self.interval_var = tk.StringVar(frame, '1')
        self.freq_var = tk.StringVar(frame, 'weekly')
        self.count_var = tk.StringVar(frame)
        self.has_end = tk.IntVar(frame, 0)
        self.end_var = tk.StringVar(frame)
        self.repeat_var.trace_add('write', lambda *_: self.set_states())
        self.end_var.trace_add('write', lambda *_: self.set_states())

        self.start = start
        self._rule = None

        num_entry_args = dict(
            width=2,
            validate='key',
            validatecommand=(frame.register(lambda s: not s or s.isdecimal()), '%P'),
        )

        repeatrow = tk.Frame(frame)
        repeatbtn = ttk.Checkbutton(
            repeatrow,
            text='Repeat ',
            variable=self.repeat_var,
        )
        repeatbtn.pack(side=tk.LEFT)
        ttk.Entry(
            repeatrow,
            textvariable=self.interval_var,
            **num_entry_args,
        ).pack(side=tk.LEFT)
        self.freq_input = ttk.Combobox(
            repeatrow,
            width=10,
            values=('hourly', 'daily', 'weekly', 'monthly', 'yearly'),
            textvariable=self.freq_var,
        )
        self.freq_input.pack(side=tk.LEFT)
        repeatrow.pack()

        freqframe = tk.Frame(frame)
        ttk.Radiobutton(
            freqframe,
            text='indefinitely',
            variable=self.end_var,
            value='indef',
        ).pack(anchor=tk.W)

        untilrow = tk.Frame(freqframe)
        ttk.Radiobutton(
            untilrow,
            text='until ',
            value='until',
            variable=self.end_var,
        ).pack(side=tk.LEFT)
        self.until = DatetimeInput(
            untilrow,
            time_var,
            (self.repeat_var, self.has_end),
        )

        countrow = tk.Frame(freqframe)
        ttk.Radiobutton(
            countrow,
            value='count',
            variable=self.end_var,
        ).pack(side=tk.LEFT)
        self.count_input = ttk.Entry(
            countrow,
            textvariable=self.count_var,
            **num_entry_args,
        )
        self.count_input.pack(side=tk.LEFT)
        count_text = ttk.Label(countrow, text=' times')
        count_text.bind('<1>', lambda e: (
            self.end_var.set('count') if self.repeat_var.get() else None))
        count_text.pack(side=tk.LEFT)
        countrow.pack(anchor=tk.W)
        freqframe.pack()
        frame.pack()

        self.end_var.set('indef')

    def set_states(self):
        def for_all_children(w):
            if isinstance(w, (ttk.Entry, ttk.Radiobutton)):
                w.state(['!'*repeat + 'disabled'])
            for c in w.children.values():
                for_all_children(c)

        end = self.end_var.get()
        repeat = self.repeat_var.get()
        for_all_children(self.frame)
        self.freq_input.config(state='readonly' if repeat else 'disabled')
        self.has_end.set(end == 'until')
        self.count_input.state(['!'*(end == 'count' and repeat) + 'disabled'])

    def get(self):
        if not self.repeat_var.get():
            return callib.RRule(self.start.get())
        attrs = {
            'FREQ': self.freq_var.get(),
            'INTERVAL': int(self.interval_var.get()),
        }
        if self.end_var.get() == 'until':
            attrs['UNTIL'] = self.until.get()
        elif self.end_var.get() == 'count':
            attrs['COUNT'] = int(self.count_var.get())
        if self._rule is None:
            return callib.RRule(self.start.get(), (attrs,))
        else:
            return self._rule.with_rule(attrs)

    def set(self, rrule):
        # no direct comparison to handle datetime.date instances
        assert rrule.dtstart.replace(tzinfo=None).ctime() == self.start.get().ctime()
        self._rule = rrule
        self.repeat_var.set(bool(rrule.rules))
        if rrule.rules:
            rule = rrule.rules[0]
            freq = rule['FREQ'].lower()
            if freq in self.freq_input.cget('values'):
                self.freq_var.set(freq)
            else:
                logging.warning('cannot set frequency to', freq)
            self.interval_var.set(rule.get('INTERVAL', 1))
            if 'UNTIL' in rule:
                self.end_var.set('until')
                self.until.set(rule['UNTIL'].astimezone(rrule.dtstart.tzinfo))
            if 'COUNT' in rule:
                self.end_var.set('count')
                self.count_var.set(rule['COUNT'])


class EventPopup:
    def __init__(self, root, callback, categories):
        self.callback = callback
        self.title_var = tk.StringVar(root)
        self.summary_var = tk.StringVar(root)
        self.description_var = tk.StringVar(root)
        self.allday_var = tk.IntVar(root)
        end_var = tk.IntVar(root)
        self.uid = str(uuid.uuid4())

        self.toplevel = toplevel = tk.Toplevel(root)
        toplevel.transient(root)
        toplevel.wait_visibility()
        toplevel.grab_set()

        ttk.Label(toplevel, textvariable=self.title_var).pack()
        self._add_labeled_entry('Summary: ', self.summary_var)
        startframe = tk.Frame(toplevel)
        ttk.Label(startframe, text='Begins on ').pack(side=tk.LEFT)
        self.start = DatetimeInput(startframe, self.allday_var, ())
        alldaybtn = ttk.Checkbutton(
            toplevel,
            text='All-day event',
            variable=self.allday_var,
        )
        alldaybtn.pack()

        endframe = tk.Frame(toplevel)
        endbtn = ttk.Checkbutton(endframe, text='Ends on ', variable=end_var)
        endbtn.pack(side=tk.LEFT)
        self.end = DatetimeInput(endframe, self.allday_var, [end_var])

        self.rrule = RRuleInput(tk.Frame(toplevel), self.start, self.allday_var)
        self.allday_var.set(0)

        self.categories = categories
        self.cat_lb = tk.Listbox(
            self.toplevel,
            height=len(self.categories),
            selectmode='multiple',
            exportselection=False,
        )
        self.cat_lb.insert(0, *self.categories)
        self.cat_lb.pack()
        self._add_labeled_entry('Description: ', self.description_var)

        btnframe = tk.Frame(toplevel)
        ttk.Button(btnframe, text='OK', command=self.on_ok).pack(side=tk.LEFT)
        ttk.Button(btnframe, text='Cancel', command=toplevel.destroy).pack(side=tk.RIGHT)
        btnframe.pack(side=tk.BOTTOM, fill=tk.X, expand=True)

    def _add_labeled_entry(self, label, var):
        frame = tk.Frame(self.toplevel)
        ttk.Label(frame, text=label).pack(side=tk.LEFT)
        ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT)
        frame.pack()

    def on_ok(self):
        try:
            start = self.start.get()
            end = self.end.get()
        except ValueError as e:
            tk_msg.showerror('error', e)
            return
        self.callback(callib.Event(
            start,
            end,
            self.summary_var.get(),
            self.description_var.get(),
            [self.categories[i] for i in self.cat_lb.curselection()],
            self.rrule.get(),
            self.uid,
        ))
        self.toplevel.destroy()


def get_handlers(root, update_cb, delete_cb):
    if update_cb is delete_cb is None:
        return lambda _: None, lambda *_: None
    return (partial(add_event, root, update_cb),
            partial(edit_event_menu, root, update_cb, delete_cb))


def add_event(root, callback, date):
    cats = tuple(filter(None, config.get('tag_colors')))
    popup = EventPopup(root, callback, cats)
    popup.title_var.set('New Event')
    popup.start.set(date)


def edit_event_menu(root, update_cb, delete_cb, event, tk_evt):
    menu = tk.Menu(root)
    cmd = partial(real_edit_event, root, update_cb, event.original)
    menu.add_command(label='Edit', command=cmd)
    menu.add_command(label='Delete', command=partial(delete_cb, event))
    if event.original != event:
        new_rule = event.rrule.with_ex(event.orig_start(tz=True))
        excl = dataclasses.replace(event.original, rrule=new_rule)
        menu.add_command(label='Exclude', command=partial(update_cb, excl))
    menu.post(tk_evt.x_root, tk_evt.y_root)


def real_edit_event(root, callback, event):
    cats = tuple({*filter(None, config.get('tag_colors')), *event.categories})
    popup = EventPopup(root, callback, cats)
    popup.title_var.set('Edit Event')
    popup.allday_var.set(event.all_day)
    popup.start.set(event.orig_start(day=True))
    popup.end.set(event.orig_end(day=True))
    popup.summary_var.set(event.summary)
    popup.description_var.set(event.description)
    for cat in event.categories:
        popup.cat_lb.selection_set(cats.index(cat))
    popup.rrule.set(event.rrule)
    popup.uid = event.uid
