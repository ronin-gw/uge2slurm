import os
import sys
import inspect
import logging

from uge2slurm.utils.py2.os import fsencode, fsdecode, access_check
from uge2slurm.utils.color import cprint

logger = logging.getLogger(__name__)

_WIN_DEFAULT_PATHEXT = ".COM;.EXE;.BAT;.CMD;.VBS;.JS;.WS;.MSC"

BIN_DIRECTORY = os.path.dirname(inspect.stack()[-1][1])


def _get_command_paths(cmd, mode=os.F_OK | os.X_OK):
    """Based on the shutil.which"""

    path = os.environ.get("PATH", None)
    if path is None:
        try:
            path = os.confstr("CS_PATH")
        except (AttributeError, ValueError):
            path = os.defpath

    if not path:
        return []

    use_bytes = isinstance(cmd, bytes)

    if use_bytes:
        path = fsencode(path)
        path = path.split(fsencode(os.pathsep))
    else:
        path = fsdecode(path)
        path = path.split(os.pathsep)

    if sys.platform == "win32":
        curdir = os.curdir
        if use_bytes:
            curdir = fsencode(curdir)
        if curdir not in path:
            path.insert(0, curdir)

        pathext_source = os.getenv("PATHEXT") or _WIN_DEFAULT_PATHEXT
        pathext = [ext for ext in pathext_source.split(os.pathsep) if ext]

        if use_bytes:
            pathext = [fsencode(ext) for ext in pathext]
        if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
            files = [cmd]
        else:
            files = [cmd + ext for ext in pathext]
    else:
        files = [cmd]

    seen = set()
    found_paths = []
    for dir in path:
        normdir = os.path.normcase(dir)
        if normdir not in seen:
            seen.add(normdir)
            for thefile in files:
                name = os.path.join(dir, thefile)
                if access_check(name, mode):
                    found_paths.append(name)

    return found_paths


def get_command_paths(cmd):
    ignore_prefix = [BIN_DIRECTORY]
    if "PYENV_ROOT" in os.environ:
        ignore_prefix.append(os.environ["PYENV_ROOT"])

    ignore_prefix = tuple(ignore_prefix)

    found_paths = []
    for path in _get_command_paths(cmd):
        if not path.startswith(ignore_prefix):
            found_paths.append(path)

    return found_paths


def get_command_path(cmd, verbose=False):
    candidates = get_command_paths(cmd)
    if len(candidates) > 1:
        if verbose:
            logger.warning('"{}" command found at mutiple paths. '
                           'Use 1st one anyway.'.format(cmd))
            cprint("\t{} -> {}".format(cmd, candidates), "yellow")
        return candidates[0]
    elif candidates:
        return candidates[0]
    else:
        return None
