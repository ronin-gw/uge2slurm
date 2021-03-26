from collections import defaultdict

from uge2slurm.utils.slurm import run_command


def get_running_jobs():
    res = run_command("squeue", ["--noheader", "--me", "--format", "%i %j"])

    name2jobid = defaultdict(set)
    for line in res.stdout.rstrip().split('\n'):
        jobid, jobname = line.split(' ', 1)
        name2jobid[jobname].add(int(jobid))

    return name2jobid
