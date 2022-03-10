"""iCal events"""
import datetime
import copy
import icalendar
from dateutil import rrule
import dateutil.tz


class Event:
    """represent a VEVENT"""
    def __init__(self, ical_component):
        """create an Event from a VEVENT component"""
        self.start = ical_component['dtstart'].dt
        self.all_day = (isinstance(self.start, datetime.date)
                        and not isinstance(self.start, datetime.datetime))
        if 'dtend' in ical_component:
            end = ical_component['dtend'].dt
            self._end_tz = getattr(end, 'tzinfo', None)
            self.duration = end - self.start
        else:
            self._end_tz = getattr(self.start, 'tzinfo', None)
            if 'duration' in ical_component:
                self.duration = ical_component['duration'].dt
            elif self.all_day:
                self.duration = datetime.timedelta(days=1)
            else:
                self.duration = datetime.timedelta(0)

        rrule_parts = []
        for prop in ('DTSTART', 'RRULE', 'EXRULE', 'RDATE', 'EXDATE'):
            if prop in ical_component:
                if isinstance(ical_component[prop], list):
                    new_parts = ical_component[prop]
                else:
                    new_parts = [ical_component[prop]]
                rrule_parts += (ical_component.content_line(prop, p) for p in new_parts)
        if len(rrule_parts) > 1:
            self.rrule = rrule.rrulestr('\n'.join(rrule_parts))
        else:
            self.rrule = rrule.rrule(rrule.DAILY, count=1, dtstart=self.start)

        if 'categories' in ical_component:
            cats = ical_component['categories']
            if not isinstance(cats, list):
                cats = [cats]
            self.categories = [c for cs in cats for c in cs.cats]
        else:
            self.categories = ()
        self.summary = ical_component.get('summary', b'')
        self.description = ical_component.get('description', b'')

    @property
    def end(self):
        if self.all_day:
            end_day = self.start.date().toordinal() + self.duration.days
            end_ts = datetime.datetime.fromordinal(end_day).timestamp()
        else:
            end_ts = self.start.timestamp() + self.duration.total_seconds()
        # Per the spec, the end is non-inclusive. I want it inclusive.
        end_ts -= datetime.time.resolution.total_seconds()
        return datetime.datetime.fromtimestamp(end_ts, self._end_tz)

    def starting_at(self, new_time):
        new = copy.copy(self)
        new.start = new_time
        return new

    def __str__(self):
        return f'<Event "{self.summary}" from {self.start} to {self.end}>'


def get_events(content):
    """Get all events"""
    return [Event(vev) for vev in icalendar.Calendar.from_ical(content).walk('VEVENT')]


def filter_events(events, start, end):
    """Yield events in the given time segment"""
    orig_start = start
    orig_end = end
    for event in events:
        if event.all_day or event.start.tzinfo is None:
            start = orig_start.replace(tzinfo=None)
            end = orig_end.replace(tzinfo=None)
        else:
            start = orig_start
            end = orig_end
        for dt in event.rrule.between(start, end):
            yield event.starting_at(dt)
