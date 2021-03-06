from __future__ import print_function

import sys
import logging
import array
import fcntl
from bisect import bisect
from functools import wraps
from termios import TIOCGWINSZ

from uge2slurm import UGE2slurmError, NAME, VERSION
from uge2slurm.utils.color import colored
from uge2slurm.utils.py2 import input


class ColorfulFormatter(logging.Formatter):
    LEVELS = (
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL
    )
    COLORS = (
        None,
        "cyan",
        "yellow",
        "red",
        "magenta"
    )

    @staticmethod
    def _get_debug_fmt():
        return colored("DEBUG: %(name)s:", color="green") + " %(msg)s"

    @classmethod
    def _get_color(cls, levelno):
        return cls.COLORS[bisect(cls.LEVELS, levelno)]

    def __init__(self, *args, **kwargs):
        """
        Python2.7 compatibility: unable to use `self._style`.
        """
        super(ColorfulFormatter, self).__init__(*args, **kwargs)
        if not hasattr(self, "_style"):
            self._style = self

    def format(self, record):
        message = super(ColorfulFormatter, self).format(record)

        if record.levelno <= logging.DEBUG:
            format_orig = self._style._fmt
            self._style._fmt = self._get_debug_fmt()
            message = logging.Formatter.format(self, record)
            self._style._fmt = format_orig
        else:
            color = self._get_color(record.levelno)
            message = colored(message, color=color)

        return message


def _set_root_logger():
    rl = logging.getLogger(NAME)

    h = logging.StreamHandler()
    h.setFormatter(ColorfulFormatter(fmt="%(levelname)s: %(msg)s"))

    rl.addHandler(h)


def entrypoint(logger):
    def _wrapper(func):
        @wraps(func)
        def _inner(*args, **kwargs):
            print("This is uge2slurm " + VERSION, file=sys.stderr)
            try:
                _set_root_logger()
                for line in sys.version.split('\n'):
                    logger.debug(line)
                sys.exit(func(*args, **kwargs))
            except KeyboardInterrupt:
                sys.exit(130)
            except UGE2slurmError as e:
                logger.critical("Error: " + e.args[0])
                sys.exit(1)

        return _inner
    return _wrapper


def print_command(command):
    print(command[0], "\\")
    i = 1
    while i < len(command) - 1:
        if command[i].startswith("--"):
            try:
                if command[i + 1].startswith("--"):
                    raise IndexError
                else:
                    print('\t', command[i], command[i + 1], "\\")
                    i += 2
            except IndexError:
                print('\t', command[i], "\\")
                i += 1
        else:
            break
    print('\t', *command[i:])


def suggest_slurm(qcommand, scommand=None):
    msg = "`{}` command is not supported.".format(qcommand)
    if scommand:
        msg += "\nPlease use `{}` instead.".format(scommand)
    msg += '\n'
    print(msg, file=sys.stderr)


def is_interactive():
    return sys.stdin.isatty() and sys.stdout.isatty()


def get_tty_width():
    buf = array.array('H', ([0] * 4))
    try:
        fcntl.ioctl(sys.stdout.fileno(), TIOCGWINSZ, buf, 1)
        return buf[1]
    except IOError:
        return 32


def confirm_command(command):
    #
    width = get_tty_width()
    print("\n{}\n".format("=====  Converted command  ".ljust(width, '=')), file=sys.stderr)
    print_command(command)
    print("\n{}\n".format('=' * width), file=sys.stderr)

    #
    while True:
        res = input("Submit? [y/N] ")
        res = res.lower()
        if res in ('y', "yes"):
            return True
        elif res in ('', 'n', 'no'):
            return False
