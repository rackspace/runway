"""Utility functions."""
from __future__ import print_function
from typing import Dict, List, Optional, Union  # noqa pylint: disable=unused-import

from contextlib import contextmanager
import importlib
import os
import platform
import stat
from subprocess import check_call
import sys

import six

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


def merge_dicts(dict1, dict2, deep_merge=True):
    """Merge y into x."""
    if deep_merge:
        if isinstance(dict1, list) and isinstance(dict2, list):
            return dict1 + dict2

        if not isinstance(dict1, dict) or not isinstance(dict2, dict):
            return dict2

        for key in dict2:
            dict1[key] = merge_dicts(dict1[key], dict2[key]) if key in dict1 else dict2[key]  # noqa pylint: disable=line-too-long
        return dict1
    else:
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


def fix_windows_command_list(commands):
    # type: (List[str]) -> List[str]
    """Return command list with working Windows commands.

    npm on windows is npm.cmd, which will blow up
    subprocess.check_call(['npm', '...'])
    """
    # This could theoretically be run for for every command, instead of just
    # limiting it to known problem commands here. Unclear which approach will
    # better, so starting with just this small list.
    for i in ['npm', 'npx']:
        if commands[0] == i:
            fully_qualified_cmd_path = which(i)
            if fully_qualified_cmd_path and (
                    not which(i, add_win_suffixes=False)):
                commands[0] = os.path.basename(fully_qualified_cmd_path)
    return commands


def run_commands(commands,  # type: List[Union[str, List[str], Dict[str, Union[str, List[str]]]]]
                 directory,  # type: str
                 env=None  # type: Optional[Dict[str, Union[str, int]]]
                ):  # noqa
    # type: (...) -> None
    """Run list of commands."""
    if env is None:
        env = os.environ.copy()
    for step in commands:
        if isinstance(step, (list, six.string_types)):
            execution_dir = directory
            raw_command = step
        elif step.get('command'):  # dictionary
            execution_dir = os.path.join(directory,
                                         step.get('cwd')) if step.get('cwd') else directory  # noqa pylint: disable=line-too-long
            raw_command = step['command']
        else:
            raise AttributeError("Invalid command step: %s" % step)
        command_list = raw_command.split(' ') if isinstance(raw_command, six.string_types) else raw_command  # noqa pylint: disable=line-too-long
        if platform.system().lower() == 'windows':
            command_list = fix_windows_command_list(command_list)

        with change_dir(execution_dir):
            check_call(command_list, env=env)


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


def which(program, add_win_suffixes=True):
    """Mimic 'which' command behavior.

    Adapted from https://stackoverflow.com/a/377028
    """
    def is_exe(fpath):
        """Determine if program exists and is executable."""
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if add_win_suffixes and platform.system().lower() == 'windows' and not (
            fname.endswith('.exe') or fname.endswith('.cmd')):
        fnames = [fname + '.exe', fname + '.cmd']
    else:
        fnames = [fname]

    for i in fnames:
        if fpath:
            exe_file = os.path.join(fpath, i)
            if is_exe(exe_file):
                return exe_file
        else:
            for path in os.environ['PATH'].split(os.pathsep):
                exe_file = os.path.join(path, i)
                if is_exe(exe_file):
                    return exe_file

    return None
