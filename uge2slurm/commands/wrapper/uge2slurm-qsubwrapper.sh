#!/bin/sh

SLURM_ENV_NAMES=(
    "SLURM_ARRAY_TASK_ID"
    "SLURM_ARRAY_TASK_MIN"
    "SLURM_ARRAY_TASK_MAX"
    "SLURM_ARRAY_TASK_STEP"
    "SLURMD_NODENAME"
    "SLURM_JOB_ID"
    "SLURM_JOB_NAME"
    "SLURM_CPUS_PER_TASK"
    "SLURM_JOB_PARTITION"
)
UGE_ENV_NAMES=(
    "SGE_TASK_ID"
    "SGE_TASK_FIRST"
    "SGE_TASK_LAST"
    "SGE_TASK_STEPSIZE"
    "HOSTNAME"
    "JOB_ID"
    "JOB_NAME"
    "NSLOTS"
    "QUEUE"
)


if [ ${#@} -eq 0 ]; then
    echo "usage: $0 command"
    echo "Convert Slurm environment variables to UGE variables"
    echo
    echo "Supported UGE variables are:"
    for v in "${UGE_ENV_NAMES[@]}" SGE_CWD_PATH RESTARTED; do
        echo "    $v"
    done
    echo
    echo 'This script is a part of "uge2slurm" python package.'
    echo

    exit
fi


for i in $(seq 0 $((${#SLURM_ENV_NAMES[@]} - 1))); do
    if [ -z "${SLURM_ENV_NAMES[$i]+x}" ] || [ -z "${UGE_ENV_NAMES[$i]+x}" ]; then
        break
    fi

    env_from="${SLURM_ENV_NAMES[$i]+x}"
    env_to="${UGE_ENV_NAMES[$i]+x}"
    export "${env_from}=${env_to}"
done

# SGE_CWD_PATH
if command -v pwd > /dev/null; then
    export SGE_CWD_PATH=$(pwd)
fi

# TODO: SGE_STDERR_PATH
# TODO: SGE_STDOUT_PATH
# TODO: SGE_STDIN_PATH
# TODO: NHOSTS
# TODO: NQUEUES

# RESTARTED
if [ "${SLURM_RESTART_COUNT}" ]; then
    if [ "$SLURM_RESTART_COUNT" -eq 0 ]; then
        export RESTARTED=0
    else
        export RESTARTED=1
    fi
fi

#
srun "$@"
