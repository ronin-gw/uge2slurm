from __future__ import absolute_import

import os.path

from uge2slurm import UGE2slurmError

WRAPPER_DIR = os.path.join(os.path.dirname(__file__), "wrapper")


class UGE2slurmCommandError(UGE2slurmError):
    pass
