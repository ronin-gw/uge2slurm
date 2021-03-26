from uge2slurm.utils.slurm import run_command


def get_partitions():
    res = run_command("sinfo", ["--noheader", "--format", "%R"])

    return set(partition for partition in res.stdout.split('\n'))
