import sys

from neotermcolor import cprint

from uge2slurm.utils.path import get_command_path
from uge2slurm.mapper import CommandMapperBase

from .argparser import get_parser, parser_args


class CommandMapper(CommandMapperBase):
    def t(self, value):
        self.args.append("--array=" + value)

    def command(self, value):
        self.args += value


def main():
    parser = get_parser()
    args = parser.parse_args()

    run(args)


def run(args):
    command_name = "sbatch"

    binary = get_command_path(command_name)
    if not binary:
        cprint("Error: command not found: " + command_name, "red", file=sys.stderr)
        if not args.dry_run:
            sys.exit(1)
        else:
            cprint("Continue dry run anyway.", "yellow", file=sys.stderr)
            binary = command_name

    converter = CommandMapper(command_name)

    if args.dry_run:
        print(converter.convert(args))
    else:
        # TODO: exec command
        raise NotImplementedError


def set_subperser(name, subparsers):
    parser = subparsers.add_parser(name, **parser_args)
    get_parser(parser)
    parser.set_defaults(func=run)
