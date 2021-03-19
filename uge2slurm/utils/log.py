import sys
import logging
from bisect import bisect
from functools import wraps

from neotermcolor import colored

from uge2slurm import UGE2slurmError


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

    @classmethod
    def _get_color(cls, levelno):
        return cls.COLORS[bisect(cls.LEVELS, levelno)]

    def format(self, record):
        message = super().format(record)
        color = self._get_color(record.levelno)
        return colored(message, color=color)


def _set_root_logger():
    rl = logging.getLogger('')

    h = logging.StreamHandler()
    h.setFormatter(ColorfulFormatter())

    rl.addHandler(h)
    # rl.setLevel(log_level)


def entrypoint(logger):
    def _wrapper(func):
        @wraps(func)
        def _inner(*args, **kwargs):
            try:
                _set_root_logger()
                sys.exit(func(*args, **kwargs))
            except KeyboardInterrupt:
                sys.exit(130)
            except UGE2slurmError as e:
                logger.critical("Error: " + e.args[0])
                sys.exit(1)

        return _inner
    return _wrapper
