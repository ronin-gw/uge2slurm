import sys
import shlex
import argparse
import logging
from gettext import gettext

from uge2slurm.utils.path import get_command_path
from uge2slurm.utils.log import entrypoint, print_command
from uge2slurm.commands import UGE2slurmCommandError

from .argparser import get_parser, parser_args, set_qsub_arguments
from .mapper import CommandMapper
from .bypass import use_qsub_if_avail

logger = logging.getLogger(__name__)


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)

    def error(self, message):
        args = {'prog': self.prog, 'message': message}
        self.exit(2, self.error_prolog + '\n' + (gettext('%(prog)s: error: %(message)s\n') % args))


@entrypoint(logger)
def main():
    #
    executed = use_qsub_if_avail()
    if executed:
        return

    #
    parser = get_parser()
    args = parser.parse_args()
    run(args)


def run(args):
    command_name = "sbatch"

    binary = get_command_path(command_name)
    if not binary:
        message = "command not found: " + command_name
        if not args.dry_run:
            raise UGE2slurmCommandError(message)
        else:
            logger.error(message)
            logger.warning("Continue dry run anyway.")
            binary = command_name

    #
    script = None
    if not args.command:
        if args.b:
            raise UGE2slurmCommandError("command required for a binary job")
        else:
            script = _read_stdin()
            if not script:
                raise UGE2slurmCommandError("no input read from stdin")
            if args.N is None:
                setattr(args, 'N', "STDIN")
    elif not args.b:
        with open(args.command[0]) as f:
            script = f.read()

    if script:
        _load_extra_args(args, script)

    converter = CommandMapper(command_name)
    converter.dry_run = args.dry_run

    command = converter.convert(args)
    if args.dry_run:
        logger.debug(args)
        print_command(command)
    else:
        # TODO: exec command
        raise NotImplementedError


def set_subperser(name, subparsers):
    parser = subparsers.add_parser(name, **parser_args)
    get_parser(parser)
    parser.set_defaults(func=run)


def _read_stdin():
    if sys.stdin.isatty():
        return
    return sys.stdin.read()


def _load_extra_args(args, script):
    prefix_string = "#$" if args.C is None else args.C
    if not prefix_string:
        return

    args_in_script = []
    for line in script.split('\n'):
        if line.startswith(prefix_string):
            args_in_script.append(line[2:].strip())
    args_in_script = ' '.join(args_in_script)

    parser = ArgumentParser()
    parser.error_prolog = "Invalid argument in the script"
    set_qsub_arguments(parser)
    extra_args = parser.parse_args(shlex.split(args_in_script))

    for dest, value in vars(extra_args).items():
        if getattr(args, dest) is None:
            setattr(args, dest, value)
