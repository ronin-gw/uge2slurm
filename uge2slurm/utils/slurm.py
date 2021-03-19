import logging
from subprocess import Popen, PIPE, CalledProcessError

from uge2slurm.utils.path import get_command_path
from uge2slurm.commands import UGE2slurmCommandError

logger = logging.getLogger(__name__)

try:  # py2 compatibility
    from subprocess import run  # novermin
except ImportError:
    class CompletedProcess(object):
        def __init__(self, args, returncode, stdout=None, stderr=None):
            self.args = args
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

        def __repr__(self):
            args = ['args={!r}'.format(self.args),
                    'returncode={!r}'.format(self.returncode)]
            if self.stdout is not None:
                args.append('stdout={!r}'.format(self.stdout))
            if self.stderr is not None:
                args.append('stderr={!r}'.format(self.stderr))
            return "{}({})".format(type(self).__name__, ', '.join(args))

        def check_returncode(self):
            if self.returncode:
                raise CalledProcessError(self.returncode, self.args, self.stdout,
                                         self.stderr)

    def run(*popenargs, **kwargs):
        input = None if "input" not in kwargs else kwargs["input"]
        check = False if "check" not in kwargs else kwargs["check"]

        if input is not None:
            if 'stdin' in kwargs:
                raise ValueError('stdin and input arguments may not both be used.')
            kwargs['stdin'] = PIPE

        with Popen(*popenargs, **kwargs) as process:
            try:
                stdout, stderr = process.communicate(input)
            except:
                process.kill()
                process.wait()
                raise
            retcode = process.poll()
            if check and retcode:
                raise CalledProcessError(retcode, process.args,
                                         output=stdout, stderr=stderr)
        return CompletedProcess(process.args, retcode, stdout, stderr)


def run_command(command_name, args, stdout=PIPE, stderr=PIPE):
    if command_name is None:
        command_name = args[0]
        args = args[1:]
    binary = get_command_path(command_name)

    try:
        if not binary:
            raise OSError
        command = [binary] + args
        return run(command, stdout=stdout, stderr=stderr, check=True,
                   universal_newlines=True)
    except OSError:
        raise UGE2slurmCommandError("Command `{}` not found.".format(command_name))
    except CalledProcessError as e:
        if e.stderr:
            logger.error(command_name + ": " + e.stderr)
        raise UGE2slurmCommandError("Failed to execute `{}` command.".format(command_name))
