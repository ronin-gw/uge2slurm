from __future__ import absolute_import

import argparse
import logging
from datetime import datetime

import uge2slurm


class _disablecoloring(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        uge2slurm.utils.color._isatty = False


class _set_logging_level(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        root_logger = logging.getLogger(uge2slurm.NAME)
        level = values
        if isinstance(level, str) and level.isdigit():
            level = int(level)

        try:
            root_logger.setLevel(level)
        except ValueError:
            if isinstance(level, str):
                level = level.upper()
                root_logger.setLevel(level)
            else:
                parser.error("Unknown logging level passed: '{}'".format(values))


def set_common_args(parser):
    parser.add_argument("-?", "--help", action="help",
                        help="show this help message and exit")
    parser.add_argument("--version", action="version", version=uge2slurm.VERSION)
    parser.add_argument("--ignore-coloring", nargs=0, action=_disablecoloring,
                        help="disable colored output")
    parser.add_argument("--verbose", nargs='?', default=logging.getLogger().level,
                        const=logging.INFO, action=_set_logging_level,
                        metavar='{"critical"|"fatal","error","warn"|"warning","info","debug",int}',
                        help='Set logging level. Default is "warning". If only '
                             '`--verbose` is given, level is set to "info".')


def get_top_parser():
    parser = argparse.ArgumentParser(description=uge2slurm.DESCRIPTION, add_help=False)
    set_common_args(parser)
    parser.set_defaults(func=None)

    return parser


def parse_ge_datetime(value):
    _value = value.split('.', 1)
    if len(_value) == 1:
        dt, seconds = _value[0], None
    else:
        dt, seconds = _value

    year = datetime.now().year

    if len(dt) == 8:
        fmt = "%m%d%H%M"
    elif len(dt) == 10:
        century = year // 100
        assert century < 100
        year = int(str(century) + dt[:2])
        value = value[2:]
        fmt = "%m%d%H%M"
    elif len(dt) == 12:
        fmt = "%Y%m%d%H%M"
    else:
        raise argparse.ArgumentError('invalid datetime format: "{}"'.format(value))

    if '.' in value:
        fmt += ".%S"

    try:
        dt = datetime.strptime(value, fmt)
    except ValueError:
        raise argparse.ArgumentError('invalid datetime format: "{}"'.format(value))

    if dt.year == 1900:
        dt = dt.replace(year=year)

    return dt
