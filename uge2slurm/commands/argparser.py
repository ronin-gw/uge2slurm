import argparse
import datetime

import neotermcolor

import uge2slurm
from . import UGE2slurmCommandError


class disablecoloring(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        neotermcolor._isatty = False


def set_common_args(parser):
    parser.add_argument("-?", "--help", action="help",
                        help="show this help message and exit")
    parser.add_argument("--version", action="version", version=uge2slurm.VERSION)
    parser.add_argument("--ignore-coloring", nargs=0, action=disablecoloring,
                        help="disable coloring output")


def get_top_parser():
    parser = argparse.ArgumentParser(description=uge2slurm.DESCRIPTION, add_help=False)
    set_common_args(parser)
    parser.set_defaults(func=None)

    return parser


def parse_ge_datetime(value):
    _value = value.split('.', 1)
    if len(value) == 1:
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
        raise UGE2slurmCommandError('invalid datetime format: "{}"'.format(value))

    if '.' in value:
        fmt += ".%S"

    try:
        dt = datetime.strptime(value, fmt)
    except ValueError:
        raise UGE2slurmCommandError('invalid datetime format: "{}"'.format(value))

    if dt.year == 1900:
        dt = dt.replace(year=year)

    return dt
