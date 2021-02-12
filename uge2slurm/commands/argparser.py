import argparse

import uge2slurm


def get_top_parser():
    parser = argparse.ArgumentParser(description=uge2slurm.DESCRIPTION)
    parser.add_argument("-v", "--version", action="version", version=uge2slurm.VERSION)

    return parser
