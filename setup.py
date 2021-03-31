from setuptools import setup, find_packages
import os.path

from uge2slurm import NAME, VERSION, DESCRIPTION

here = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(here, "README.md")) as f:
    long_description = f.read()

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ronin-gw/uge2slurm",
    author="Hayato Anzawa",
    author_email="anzawa@sb.ecei.tohoku.ac.jp",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Topic :: System :: Clustering",
        "Topic :: System :: Distributed Computing",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9"
    ],
    keywords="SGE, UGE, Slurm",
    packages=find_packages(),
    python_requires=">=2.7, !=3.0, !=3.1, <4",
    entry_points={
        "console_scripts": [
            "uge2slurm = uge2slurm.commands.uge2slurm:main",
            "qsub = uge2slurm.commands.qsub:main"
        ]
    },
    package_dir={"uge2slurm.commands": "uge2slurm/commands"},
    package_data={
        "uge2slurm.commands": ["wrapper/*.sh"]
    }
)
