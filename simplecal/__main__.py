"""Entrypoint"""
import argparse
import json
import sys
import os
import logging
import datetime

__version__ = 'dev'


def get_args():
    parser = argparse.ArgumentParser(description='A simple Python/Tk iCalendar viewer.')
    parser.add_argument('-f', '--config-file', help='Use an alternative config file.')
    parser.add_argument('-C', '--add-config', type=json.loads, default={},
    help='Add the given JSON to the configuration for this run only.')
    parser.add_argument('-c', '--add-calendar', action='append',
    help='Add the given calendar without removing already configured ones.')
    parser.add_argument('-m', '--month', type=lambda s: (int(s[:4]), int(s[5:])),
    # if you run this on Dec 31. at 23:59:59.999, problems are your own fault
    default=(datetime.date.today().year, datetime.date.today().month),
    help='Show the given month (YYYY-MM) instead of the current one.')
    parser.add_argument('-V', '--version', action='store_true',
    help='Show version and exit.')
    parser.add_argument('-v', '--verbose', action='count', default=0,
    help='Increase verbosity. Repeat for greater increase.')
    parser.add_argument('-q', '--quiet', action='count', default=0,
    help='Decrease verbosity. Repeat for greater decrease.')
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
    from . import calgui

    if args.config_file:
        config.config_file = args.config_file
    config.load()
    config.patch(args.add_config)
    if args.add_calendar:
        config.patch({'calendars': config.get('calendars') + args.add_calendar})
    calgui.run_app(*args.month)


if __name__ == '__main__':
    main(get_args())
