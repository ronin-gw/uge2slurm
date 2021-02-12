import os
import sys
import inspect
from shutil import _access_check

_WIN_DEFAULT_PATHEXT = ".COM;.EXE;.BAT;.CMD;.VBS;.JS;.WS;.MSC"

BIN_DIRECTORY = os.path.dirname(inspect.stack()[1].filename)


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
        path = os.fsencode(path)
        path = path.split(os.fsencode(os.pathsep))
    else:
        path = os.fsdecode(path)
        path = path.split(os.pathsep)

    if sys.platform == "win32":
        curdir = os.curdir
        if use_bytes:
            curdir = os.fsencode(curdir)
        if curdir not in path:
            path.insert(0, curdir)

        pathext_source = os.getenv("PATHEXT") or _WIN_DEFAULT_PATHEXT
        pathext = [ext for ext in pathext_source.split(os.pathsep) if ext]

        if use_bytes:
            pathext = [os.fsencode(ext) for ext in pathext]
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
                if _access_check(name, mode):
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
