from __future__ import print_function

import argparse
import subprocess
import logging

from uge2slurm.utils.path import get_command_path
from uge2slurm.utils.log import print_command
from uge2slurm.utils.slurm import run
from uge2slurm.commands import UGE2slurmCommandError

from .argparser import set_orig_argsuments

logger = logging.getLogger(__name__)


def use_qsub_if_avail():
    qsub = get_command_path("qsub")
    if qsub is None:
        return

    parser = argparse.ArgumentParser(add_help=False)
    set_orig_argsuments(parser)
    orig_args, qsub_args = parser.parse_known_args()

    logger.info('"qsub" command is found. Execute qsub with given arguments.')

    command = [qsub] + qsub_args
    if orig_args.dry_run:
        logger.debug(orig_args)
        print_command(command)
        return True

    try:
        res = run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                  check=True, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        if e.stderr:
            logger.error("squeue: " + e.stderr)
        raise UGE2slurmCommandError("Failed to execute `squeue` command.")

    print(res.stdout, end='')

    return True
