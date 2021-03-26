import logging
from subprocess import PIPE, CalledProcessError
from uge2slurm.utils.py2.subprocess import run

from uge2slurm.utils.path import get_command_path
from uge2slurm.commands import UGE2slurmCommandError

logger = logging.getLogger(__name__)


def run_command(command_name, args, stdout=PIPE, stderr=PIPE):
    if command_name is None:
        command_name = args[0]
        args = args[1:]
    binary = get_command_path(command_name)

    try:
        if not binary:
            raise OSError
        command = [binary] + args
        logger.debug("Run command: {}".format(command))
        return run(command, stdout=stdout, stderr=stderr, check=True,
                   universal_newlines=True)
    except OSError:
        raise UGE2slurmCommandError("Command `{}` not found.".format(command_name))
    except CalledProcessError as e:
        if e.stderr:
            logger.error(command_name + ": " + e.stderr)
        raise UGE2slurmCommandError("Failed to execute `{}` command.".format(command_name))
