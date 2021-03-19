import subprocess
import logging
from collections import defaultdict

from uge2slurm.utils.path import get_command_path
from uge2slurm.commands import UGE2slurmCommandError

logger = logging.getLogger(__name__)


def get_running_jobs():
    command = [None, "--noheader", "--me", "--format", "%i %j"]
    squeue = get_command_path("squeue")

    try:
        if not squeue:
            raise FileNotFoundError
        command[0] = squeue[0]
        res = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=15, check=True, universal_newlines=True)
    except FileNotFoundError:
        raise UGE2slurmCommandError("Command `squeue` not found.")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        if e.stderr:
            logger.error("squeue: " + e.stderr)
        raise UGE2slurmCommandError("Failed to execute `squeue` command.")

    name2jobid = defaultdict(set)
    for line in res.stdout:
        jobid, jobname = line.split(' ', 1)
        name2jobid[jobname].add(int(jobid))

    return name2jobid
