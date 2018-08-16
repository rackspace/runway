"""Utility functions."""
from __future__ import print_function

from contextlib import contextmanager
import importlib
import os
import platform
import stat
import sys

EMBEDDED_LIB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'embedded'
)


@contextmanager
def change_dir(newdir):
    """Change directory.

    Adapted from http://stackoverflow.com/a/24176022
    """
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


def ensure_file_is_executable(path):
    """Exit if file is not executable."""
    if platform.system() != 'Windows' and (
            not stat.S_IXUSR & os.stat(path)[stat.ST_MODE]):
        print("Error: File %s is not executable" % path)
        sys.exit(1)


def load_object_from_string(fqcn):
    """Convert "." delimited strings to a python object.

    Given a "." delimited string representing the full path to an object
    (function, class, variable) inside a module, return that object.  Example:
    load_object_from_string("os.path.basename")
    load_object_from_string("logging.Logger")
    load_object_from_string("LocalClassName")

    Adapted from stacker.utils
    """
    module_path = "__main__"
    object_name = fqcn
    if "." in fqcn:
        module_path, object_name = fqcn.rsplit(".", 1)
        importlib.import_module(module_path)
    return getattr(sys.modules[module_path], object_name)


def merge_dicts(dict1, dict2):
    """Merge y into x."""
    dict3 = dict1.copy()
    dict3.update(dict2)
    return dict3
    # Alternate py3 version:
    # if sys.version_info > (3, 4):
    #     return {**dict1, **dict2}


def get_embedded_lib_path():
    """Return path of embedded libraries."""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'embedded'
    )


@contextmanager
def ignore_exit_code_0():
    """Capture exit calls and ignore those with exit code 0."""
    try:
        yield
    except SystemExit as exit_exc:
        if exit_exc.code != 0:
            raise


@contextmanager
def use_embedded_pkgs(embedded_lib_path=None):
    """Temporarily prepend embedded packages to sys.path."""
    if embedded_lib_path is None:
        embedded_lib_path = get_embedded_lib_path()

    old_sys_path = list(sys.path)
    sys.path.insert(
        1,  # https://stackoverflow.com/a/10097543
        embedded_lib_path
    )
    try:
        yield
    finally:
        sys.path = old_sys_path


def which(program):
    """Mimic 'which' command behavior.

    Adapted from https://stackoverflow.com/a/377028
    """
    def is_exe(fpath):
        """Determine if program exists and is executable."""
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, _fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None
