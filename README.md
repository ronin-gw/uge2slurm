uge2slurm
=========

[![PyPI version](https://img.shields.io/pypi/v/uge2slurm.svg)](https://pypi.org/project/uge2slurm/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/uge2slurm.svg)](https://pypi.org/project/uge2slurm/)

Grid Engine to Slurm command converter

* * *

uge2slurm provides conversion from `qsub` command in UGE/SGE to Slurm's `sbatch`
command.

After installation, the following commands are available.
- uge2slurm [{qsub}]
- qsub \<qsub args>

## Command usage

These options are commonly available for all subcommands.

#### -?/--help
Show help message and exit.

#### --version
Show version info and exit.

#### --ignore-coloring
Disable colored output.

#### --verbose [{"critical"|"fatal","error","warn"|"warning","info","debug",int}]
Set verbosity in Python logging level. Default is "warning". If only `--verbose`
flag is given, level is set to info.


### uge2slurm
List Grid Engine and Slurm commands' existence and exit.

### qsub
Convert `qsub` command to `sbatch` command and execute.  
The following options can be specified besides `qsub` arguments.

#### -n/--dry-run
Print converted Slurm command and exit.

#### --memory resource [...]
Specify which resource value should be mapped into `--mem-per-cpu` option.
If multiple values are specified, the first valid value will be used.

#### --cpus parallel_env [...]
Specify which parallel_environment should be mapped into `--cpus-per-task` option.
If multiple values are specified, the first valid value will be used.  
Note that range values are not supported and its minimum value will be used as
the number of cpus.

#### --partition resource=partition [...]
Specify which resource name should be mapped into partition (queue) via
`--partition` option. Resource-partition pairs must be specified by '='
separated strings.

The partition mapping is solved by the following order:
1. use relations specified by `--partition` option when the partition name is
   exactly matched.
2. split partition name by punctuations except '-' and '_' then try exact match
   on the prefix and resource names.
3. try forward matching on partition names and resource names.

Examples:
```
% sinfo --format "%P"
PARTITION
gpu.q
gpu_intr.q

% uge2slurm qsub -n -l gpu_in test.sh
sbatch
	 --partition gpu_intr.q

% uge2slurm qsub -n -l gp test.sh
ERROR: Resource specification "gp" matches multiple partitions.
WARNING: 	gp -> gpu.q, gpu_intr.q
WARNING: Try to add implicit mapping option like `--partition gp=gpu.q`.
CRITICAL: Error: failed to map resource into partition.

% uge2slurm qsub -n -l gpu test.sh
sbatch
	 --partition gpu.q

% uge2slurm qsub -n --partition gpu=gpu_intr -l gpu test.sh
sbatch
    --partition gpu_intr
```
