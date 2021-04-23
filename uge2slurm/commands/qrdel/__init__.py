import logging

from uge2slurm.utils.log import entrypoint, suggest_slurm

logger = logging.getLogger(__name__)


@entrypoint(logger)
def main():
    suggest_slurm("qrdel")
