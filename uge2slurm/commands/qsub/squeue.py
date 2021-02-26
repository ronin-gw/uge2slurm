import subprocess
import logging
from collections import defaultdict

from uge2slurm.commands import UGE2slurmCommandError

logger = logging.getLogger(__name__)


def get_running_jobs():
    command = ["squeue", "--noheader", "--me", "--format", "%i %j"]

    try:
        res = subprocess.run(command, capture_output=True, timeout=15, check=True,
                             universal_newlines=True)
    except FileNotFoundError:
        logger.critical("Command `squeue` not found.")
        raise UGE2slurmCommandError
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.critical("Failed to execute `squeue` command.")
        if e.stderr:
            logger.error("squeue: " + e.stderr)
        raise UGE2slurmCommandError

    name2jobid = defaultdict(set)
    for line in res.stdout:
        jobid, jobname = line.split(' ', 1)
        name2jobid[jobname].add(int(jobid))

    return name2jobid
