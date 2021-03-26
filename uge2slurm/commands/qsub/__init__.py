import logging

from uge2slurm.utils.path import get_command_path
from uge2slurm.utils.log import entrypoint, print_command
from uge2slurm.utils.slurm import run_command
from uge2slurm.commands import UGE2slurmCommandError

from .argparser import get_parser, parser_args
from .mapper import CommandMapper

logger = logging.getLogger(__name__)


@entrypoint(logger)
def main():
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

    converter = CommandMapper(command_name, dry_run=args.dry_run)
    command = converter.convert(args)

    if args.dry_run:
        logger.debug(args)
        print_command(command)
        return

    run_command(None, command, stdout=None, stderr=None)


def set_subperser(name, subparsers):
    parser = subparsers.add_parser(name, **parser_args)
    get_parser(parser)
    parser.set_defaults(func=run)
