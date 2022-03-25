"""Entrypoint"""
import argparse
import json
import sys
import logging
import datetime
import functools

import dateutil.parser

__version__ = 'dev'


def get_args():
    parser = argparse.ArgumentParser(description='A simple Python/Tk iCalendar viewer.')
    parser.add_argument('-f', '--config-file', help='Use an alternative config file.')
    parser.add_argument('-C', '--add-config', type=json.loads, default={},
    help='Add the given JSON to the configuration for this run only.')
    parser.add_argument('-w', '--write-calendar',
    help='Write edits to this calendar')
    parser.add_argument('-d', '--display',
    type=functools.partial(dateutil.parser.parse, dayfirst=True),
    default=datetime.date.today(),
    help='Show the given date instead of the current one.')
    parser.add_argument('-V', '--version', action='store_true',
    help='Show version and exit.')
    parser.add_argument('-v', '--verbose', action='count', default=0,
    help='Increase verbosity. Repeat for greater increase.')
    parser.add_argument('-q', '--quiet', action='count', default=0,
    help='Decrease verbosity. Repeat for greater decrease.')
    parser.add_argument('calendar', nargs='*', help='Calendar to display')
    return parser.parse_args()


def main(args):
    log_levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL+1]
    logging.basicConfig(
        format='%(levelname)s - %(message)s',
        level=log_levels[sorted((0, args.quiet-args.verbose+2, 4))[1]],
    )
    logging.debug('started with %s', sys.argv)
    if args.version:
        print('simplecal version', __version__)
        sys.exit()

    # import only after logging is set up
    from . import config
    from . import gui
    from . import callib

    if args.config_file:
        config.config_file = args.config_file
    config.load()
    config.patch(args.add_config)

    calendars = []
    if args.write_calendar:
        try:
            calendars.append(callib.Calendar(args.write_calendar))
        except Exception as e:
            logging.error(f'Failed to read calendar file "{args.write_calendar}": {e}')
            sys.exit(1)
    for c in args.calendar:
        try:
            calendars.append(callib.Calendar(c))
        except Exception as e:
            logging.error(f'Failed to read calendar file "{c}": {e}')

    gui.run_app(args.display, calendars, bool(args.write_calendar))


if __name__ == '__main__':
    main(get_args())
