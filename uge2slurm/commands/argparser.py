import argparse

import neotermcolor

import uge2slurm


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
