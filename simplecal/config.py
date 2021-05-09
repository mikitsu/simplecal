"""configuration management"""
import json
import calendar
import os
import functools
import logging

__all__ = ['get', 'patch', 'load', 'save']

config_file = os.path.join(
    os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
    'simplecal', 'config.json',
)
DEFAULT = {
    'calendars': [],
    'days_of_week': list(calendar.day_abbr),
    'week_starts_on': 0,
    'time_format': '%H:%M',
    'lum_threshold': 140,
    'grey_factor': 0.5,
    'tag_colors': {
        '': '#bbbb88',
    },
    'styles': {
        'default': {},
        'dayOfWeek': {},
        'dateNumber': {},
        'dateCell': {},
        'eventDisplay': {
            'padx': 10,
        },
    },
    'direct_styles': {},
}
config = DEFAULT
patches = {}


def merge(conf1, conf2):
    """Recursively merge ``conf1`` and ``conf2``; ``conf2`` wins on same keys."""
    if not (isinstance(conf1, dict) and isinstance(conf2, dict)):
        if isinstance(conf1, dict) or isinstance(conf2, dict):
            raise TypeError('conf1 and conf2 must both be dicts or not,'
                            f' not {conf1!r} and {conf2!r}.')
        else:
            return conf2
    new = {}
    for k in conf1.keys() - conf2.keys():
        new[k] = conf1[k]
    for k in conf2.keys() - conf1.keys():
        new[k] = conf2[k]
    for k in conf1.keys() & conf2.keys():
        new[k] = merge(conf1[k], conf2[k])
    return new


@functools.lru_cache
def get(*path):
    r = merge(config, patches)
    for c in path:
        r = r[c]
    return r


def patch(data):
    global patches
    patches = merge(patches, data)
    get.cache_clear()


def load():
    logging.info('loading config file %s', config_file)
    get.cache_clear()
    global config
    try:
        with open(config_file) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        data = {}
        logging.error('error reading config file: %s', e)
    config = merge(DEFAULT, data)


def save(data):
    global config
    with open(config_file, 'w') as f:
        json.dump(data, f)
    logging.info('wrote configuration to %s', config_file)
    config = data
    get.cache_clear()
