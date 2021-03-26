from __future__ import absolute_import

from subprocess import Popen, PIPE, CalledProcessError


try:
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

    class _Popen(Popen):
        """
        Backport for context manager support.
        source: https://github.com/python/cpython/blob/2d1cbe4193499914ccc9d217ea63eb17ff927c91/Lib/subprocess.py
        """
        def __init__(self, args, *_args, **kwargs):
            self.args = args
            super(_Popen, self).__init__(args, *_args, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, value, traceback):
            if self.stdout:
                self.stdout.close()
            if self.stderr:
                self.stderr.close()
            try:
                if self.stdin:
                    self.stdin.close()
            finally:
                if exc_type == KeyboardInterrupt:
                    return
                self.wait()

    def run(*popenargs, **kwargs):
        input = None if "input" not in kwargs else kwargs["input"]
        check = False if "check" not in kwargs else kwargs.pop("check")

        if input is not None:
            if 'stdin' in kwargs:
                raise ValueError('stdin and input arguments may not both be used.')
            kwargs['stdin'] = PIPE

        with _Popen(*popenargs, **kwargs) as process:
            try:
                stdout, stderr = process.communicate(input)
            except:  # noqa
                process.kill()
                process.wait()
                raise
            retcode = process.poll()
            if check and retcode:
                raise CalledProcessError(retcode, process.args,
                                         output=stdout, stderr=stderr)
        return CompletedProcess(process.args, retcode, stdout, stderr)
