from __future__ import absolute_import

import sys
import os


try:
    from os import fsencode, fsdecode  # novermin
    from shutil import _access_check as access_check
except ImportError:
    _encoding = sys.getfilesystemencoding()

    def fsencode(filename):
        if isinstance(filename, str):
            return filename.encode(_encoding)
        else:
            return filename

    def fsdecode(filename):
        if isinstance(filename, bytes):
            return filename.decode(_encoding)
        else:
            return filename

    def access_check(fn, mode):
        return (os.path.exists(fn) and os.access(fn, mode) and not os.path.isdir(fn))
