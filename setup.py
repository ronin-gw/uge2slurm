from setuptools import setup, find_packages
import pathlib

from uge2slurm import NAME, VERSION, DESCRIPTION

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ronin_gw/uge2slurm",
    author="Hayato Anzawa",
    author_email="anzawa@sb.ecei.tohoku.ac.jp",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Topic :: System :: Clustering",
        "Topic :: System :: Distributed Computing"
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only"
    ],
    keywords="SGE, UGE, Slurm",
    packages=find_packages(),
    python_requires=">=3.6, <4",
    install_requires=["neotermcolor"],
    entry_points={
        "console_scripts": [
            "uge2slurm = uge2slurm.commands.uge2slurm:main",
            "qsub = uge2slurm.commands.qsub:main"
        ]
    }
)
