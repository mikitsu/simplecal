from __future__ import annotations
"""iCal events"""
import datetime
import dataclasses
import logging
import uuid
import sys
import re
import icalendar
import dateutil.rrule as du_rrule
import dateutil.tz


def force_tz(dt):
    if not isinstance(dt, datetime.datetime):
        dt = datetime.datetime.combine(dt, datetime.time())
    if dt.tzinfo is None:
        return dt.replace(tzinfo=dateutil.tz.gettz())
    else:
        return dt


@dataclasses.dataclass
class RRule:
    """wrapper around dateutil.rruleset"""
    dtstart: datetime.datetime
    rules: tuple[dict] = ()
    inc_dates: tuple[datetime.date] = ()
    ex_dates: tuple[datetime.date] = ()

    du_rules: list[du_rrule.rrule] = dataclasses.field(init=False)
    ruleset: du_rrule.rruleset = dataclasses.field(init=False)

    def __post_init__(self):
        self.dtstart = force_tz(self.dtstart)
        self.du_rules = []
        self.ruleset = du_rrule.rruleset(cache=True)
        for rule in self.rules:
            if 'UNTIL' in rule:
                rule['UNTIL'] = rule['UNTIL'].astimezone(dateutil.tz.UTC)
            rule = du_rrule.rrulestr(
                icalendar.vRecur(rule).to_ical().decode(),
                dtstart=self.dtstart,
            )
            self.ruleset.rrule(rule)
            self.du_rules.append(rule)
        for dt in self.inc_dates:
            self.ruleset.rdate(force_tz(dt))
        for dt in self.ex_dates:
            self.ruleset.exdate(force_tz(dt))

    def with_rule(self, rule):
        if len(self.rules) not in (0, 1):
            logging.warning('replacing multiple rrules with a single one')
        return dataclasses.replace(self, rules=(rule,))

    def with_inc(self, dt):
        return dataclasses.replace(self, inc_dates=self.inc_dates + (dt,))

    def with_ex(self, dt):
        return dataclasses.replace(self, ex_dates=self.ex_dates + (dt,))


@dataclasses.dataclass
class Event:
    """represent a VEVENT"""
    start: datetime.datetime
    end: datetime.datetime
    summary: str
    description: str
    categories: list[str]
    rrule: RRule
    uid: str = dataclasses.field(default_factory=uuid.uuid4)
    mod_stamp: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.now(dateutil.tz.UTC))
    if sys.version_info >= (3, 10):
        _: dataclasses.KW_ONLY
    all_day: bool = None
    original: Event = dataclasses.field(init=False)
    _had_tz: bool = None

    def __post_init__(self):
        self.original = self
        if self.all_day is None:
            self.all_day = not isinstance(self.start, datetime.datetime)
        else:
            assert isinstance(self.start, datetime.datetime)
        if self._had_tz is None:
            self._had_tz = getattr(self.start, 'tzinfo', None) is not None
        self.start = force_tz(self.start)

        if self.end is not None:
            self.end = force_tz(self.end)
        elif self.all_day:
            self.end = datetime.datetime.replace(
                datetime.datetime.fromordinal(self.start.toordinal() + 1),
                tzinfo=self.start.tzinfo,
            )
        else:
            self.end = self.start + datetime.datetime.resolution

        if not (self.rrule.rules or self.rrule.inc_dates):
            self.rrule.ruleset.rdate(self.start)

    @property
    def duration(self):
        return self.end - self.start

    @classmethod
    def from_vevent(cls, ical_component):
        """create an Event from a VEVENT component"""
        start = ical_component['dtstart'].dt

        end = None
        if 'dtend' in ical_component:
            end = ical_component['dtend'].dt
        elif 'duration' in ical_component:
            end = start + ical_component['duration'].dt

        if 'categories' in ical_component:
            catss = ical_component['categories']
            if not isinstance(catss, list):
                catss = [catss]
        else:
            catss = []

        def get_list(key):
            v = ical_component.get(key, [])
            return v if isinstance(v, list) else [v]

        rrule = RRule(
            start,
            tuple({k: v for k, [v] in r.items()} for r in get_list('rrule')),
            tuple(d.dt for ds in get_list('rdate') for d in ds.dts),
            tuple(d.dt for ds in get_list('exdate') for d in ds.dts),
        )

        return cls(
            start,
            end,
            str(ical_component.get('summary', '')),
            str(ical_component.get('description', '')),
            [cat for cats in catss for cat in cats.cats],
            rrule,
            str(ical_component['uid']),
            ical_component['dtstamp'].dt,
        )

    def starting_at(self, new_start):
        new_end = self.end + (new_start - self.start)
        r = dataclasses.replace(self, start=new_start, end=new_end)
        r.original = self.original
        return r

    def __str__(self):
        return f'<Event "{self.summary}" from {self.start} to {self.end}>'

    def to_component(self):
        r = icalendar.Event()
        val_re = re.compile(r'(UNTIL=\d{8}T\d{6})')
        for rule in self.rrule.du_rules:
            for line in str(rule).split('\n'):
                key, value = line.split(':', 1)
                if key != 'DTSTART':
                    assert key == 'RRULE', key
                    # our until value is always UTC internally
                    value = val_re.sub('\\1Z', value, count=1)
                    r.add(key, icalendar.vRecur.from_ical(value))
        for dt in self.rrule.inc_dates:
            r.add('rdate', dt)
        for dt in self.rrule.ex_dates:
            r.add('exdate', dt)

        r.add('dtstart', self.orig_start(tz=True, day=True))
        r.add('dtend', self.orig_end(tz=True, day=True))
        if self.summary:
            r.add('summary', self.summary)
        if self.description:
            r.add('description', self.description)
        if self.categories:
            r.add('categories', self.categories)
        r.add('uid', self.uid)
        r.add('dtstamp', self.mod_stamp)
        return r

    def _mk_orig_dt(attr):
        def orig_(self, *, tz=False, day=False):
            r = getattr(self, attr)
            if tz and not self._had_tz:
                r = r.replace(tzinfo=None)
            if day and self.all_day:
                r = r.date()
            return r
        orig_.__name__ += attr
        return orig_

    orig_start = _mk_orig_dt('start')
    orig_end = _mk_orig_dt('end')
    del _mk_orig_dt


class Calendar:
    def __init__(self, file):
        with open(file) as f:
            data = f.read()
        self.file = file
        self.ical = icalendar.Calendar.from_ical(data)
        self.events = {}
        self.other_comps = []
        for comp in self.ical.subcomponents:
            if comp.name == 'VEVENT':
                self.events[str(comp['uid'])] = Event.from_vevent(comp)
            else:
                self.other_comps.append(comp)

    def write(self):
        event_comps = [evt.to_component() for evt in self.events.values()]
        self.ical.subcomponents = self.other_comps + event_comps
        with open(self.file, 'wb') as f:
            f.write(self.ical.to_ical())


def filter_events(events, start, end):
    """Yield events in the given time segment"""
    for event in events:
        for dt in event.rrule.ruleset.between(start - event.duration, end):
            yield event.starting_at(dt)
