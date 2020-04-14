"""Utility functions."""
from __future__ import print_function
from typing import Any, Dict, Iterator, List, Optional, Union  # noqa pylint: disable=unused-import

from contextlib import contextmanager
import hashlib
import importlib
import json
import os
import platform
import re
import stat
from subprocess import check_call
import sys
import six

AWS_ENV_VARS = ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                'AWS_SESSION_TOKEN')
EMBEDDED_LIB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'embedded'
)


class cached_property(object):  # noqa pylint: disable=invalid-name,too-few-public-methods
    """Decorator for creating cached properties.

    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Deleting the attribute resets the property.
    Source: https://github.com/bottlepy/bottle/commit/fa7733e075da0d790d809aa3d2f53071897e6f76

    """

    def __init__(self, func):
        """Initialize class.

        Args:
            func (Callable): Method being decorated.

        """
        self.func = func

    def __get__(self, obj, _):
        """Attempt to get a cached value.

        Args:
            obj (Any): Instance of a class.

        Returns:
            Any

        """
        if obj is None:
            return self

        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


# python2 supported pylint is unable to load six.moves correctly
class MutableMap(six.moves.collections_abc.MutableMapping):  # pylint: disable=no-member
    """Base class for mutable map objects."""

    def __init__(self, **kwargs):
        # type: (Dict[str, Any]) -> None
        """Initialize class.

        Provided ``kwargs`` are added to the object as attributes.

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                print(obj.__dict__)
                # {'key': 'value'}

        """
        for key, value in kwargs.items():
            if isinstance(value, dict):
                setattr(self, key, MutableMap(**value))
            else:
                setattr(self, key, value)
        if kwargs:
            self._found_queries = MutableMap()

    @property
    def data(self):
        # type: () -> Dict[str, Any]
        """Sanitized output of __dict__.

        Removes anything that starts with ``_``.

        """
        result = {}
        for key, val in self.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(val, MutableMap):
                result[key] = val.data
            else:
                result[key] = val
        return result

    def clear_found_cache(self):
        # type: () -> None
        """Clear _found_cache."""
        for _, val in self.__dict__.items():
            if isinstance(val, MutableMap):
                val.clear_found_cache()
        if hasattr(self, '_found_queries'):
            self._found_queries.clear()

    def find(self, query, default=None, ignore_cache=False):
        # type: (str, Any, bool) -> Any
        """Find a value in the map.

        Previously found queries are cached to increase search speed. The
        cached value should only be used if values are not expected to change.

        Args:
            query: A period delimited string that is split to search for
                nested values
            default: The value to return if the query was unsuccessful.
            ignore_cache: Ignore cached value.

        """
        if not hasattr(self, '_found_queries'):
            # if not created from kwargs, this attr won't exist yet
            # this is done to prevent endless recursion
            self._found_queries = MutableMap()

        if not ignore_cache:
            cached_result = self._found_queries.get(query, None)
            if cached_result:
                return cached_result

        split_query = query.split('.')

        if len(split_query) == 1:
            result = self.get(split_query[0], default)
            if result != default:
                self._found_queries[split_query[0]] = result
            return result

        nested_value = self.get(split_query[0])

        if not nested_value:
            return default

        nested_value = nested_value.find(split_query[1])

        try:
            nested_value = self[split_query[0]].find('.'.join(split_query[1:]),
                                                     default, ignore_cache)
            if nested_value != default:
                self._found_queries[query] = nested_value
            return nested_value
        except (AttributeError, KeyError):
            return default

    def get(self, key, default=None):
        # type: (str, Any) -> Any
        """Implement evaluation of self.get.

        Args:
            key: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        return getattr(self, key, default)

    def __bool__(self):
        # type: () -> bool
        """Implement evaluation of instances as a bool."""
        if self.data:
            return True
        return False

    def __contains__(self, value):
        # type: () -> bool
        """Implement evaluation of 'in' conditional."""
        return value in self.data

    __nonzero__ = __bool__  # python2 compatability

    def __getitem__(self, key):
        # type: (str) -> Any
        """Implement evaluation of self[key].

        Args:
            key: Attribute name to return the value for.

        Returns:
            The value associated with the provided key/attribute name.

        Raises:
            Attribute: If attribute does not exist on this object.

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                print(obj['key'])
                # value

        """
        return getattr(self, key)

    def __setitem__(self, key, value):
        # type: (str, Any) -> None
        """Implement assignment to self[key].

        Args:
            key: Attribute name to associate with a value.
            value: Value of a key/attribute.

        Example:
            .. codeblock: python

                obj = MutableMap()
                obj['key'] = 'value'
                print(obj['key'])
                # value

        """
        if isinstance(value, dict):
            setattr(self, key, MutableMap(**value))
        else:
            setattr(self, key, value)

    def __delitem__(self, key):
        # type: (str) -> None
        """Implement deletion of self[key].

        Args:
            key: Attribute name to remove from the object.

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                del obj['key']
                print(obj.__dict__)
                # {}

        """
        delattr(self, key)

    def __len__(self):
        # type: () -> int
        """Implement the built-in function len().

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                print(len(obj))
                # 1

        """
        return len(self.__dict__)

    def __iter__(self):
        # type: () -> Iterator[Any]
        """Return iterator object that can iterate over all attributes.

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                for k, v in obj.items():
                    print(f'{key}: {value}')
                # key: value

        """
        return iter(self.__dict__)

    def __str__(self):
        # type: () -> str
        """Return string representation of the object."""
        return json.dumps(self.data)


@contextmanager
def argv(*args):
    # type: (str) -> None
    """Context manager for temporarily changing sys.argv."""
    # passing to list() creates a new instance
    original_argv = list(sys.argv)  # TODO use .copy() after dropping python 2
    try:
        sys.argv = list(args)  # convert tuple to list
        yield
    finally:
        # always restore original value
        sys.argv = original_argv


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


@contextmanager
def environ(env=None, **kwargs):
    """Context manager for temporarily changing os.environ.

    The original value of os.environ is restored upon exit.

    Args:
        env (Dict[str, str]): Dictionary to use when updating os.environ.

    """
    env = env or {}
    env.update(kwargs)

    original_env = {key: os.getenv(key) for key in env}
    os.environ.update(env)

    try:
        yield
    finally:
        # always restore original values
        for key, val in original_env.items():
            if val is None:
                del os.environ[key]
            else:
                os.environ[key] = val


def load_object_from_string(fqcn, try_reload=False):
    """Convert "." delimited strings to a python object.

    Args:
        fqcn (str): A "." delimited string representing the full path to an
            object (function, class, variable) inside a module
        try_reload (bool): Try to reload the module so any global variables
            set within the file during import are reloaded. This only applies
            to modules that are already imported and are not builtin.

    Returns:
        Any: Object being imported from the provided path.

    Example::

        load_object_from_string("os.path.basename")
        load_object_from_string("logging.Logger")
        load_object_from_string("LocalClassName")

    """
    module_path = "__main__"
    object_name = fqcn
    if '.' in object_name:
        module_path, object_name = fqcn.rsplit('.', 1)
        if (
                try_reload and
                sys.modules.get(module_path) and
                module_path.split('.')[0] not in sys.builtin_module_names  # skip builtins
        ):
            # TODO remove is next major release; backport circumvents expected functionality
            #
            # pylint<2.3.1 incorrectly identifies this
            # pylint: disable=too-many-function-args
            six.moves.reload_module(sys.modules[module_path])
        else:
            importlib.import_module(module_path)
    return getattr(sys.modules[module_path], object_name)


def merge_dicts(dict1, dict2, deep_merge=True):
    """Merge dict2 into dict1."""
    if deep_merge:
        if isinstance(dict1, list) and isinstance(dict2, list):
            return dict1 + dict2

        if not isinstance(dict1, dict) or not isinstance(dict2, dict):
            return dict2

        for key in dict2:
            dict1[key] = merge_dicts(dict1[key], dict2[key]) if key in dict1 else dict2[key]  # noqa pylint: disable=line-too-long
        return dict1
    dict3 = dict1.copy()
    dict3.update(dict2)
    return dict3
    # Alternate py3 version:
    # (tbd if it does or doesn't deep merge, and if that is needed)
    # if sys.version_info > (3, 4):
    #     return {**dict1, **dict2}


def extract_boto_args_from_env(env_vars):
    """Return boto3 client args dict with environment creds."""
    boto_args = {}
    for i in ['aws_access_key_id', 'aws_secret_access_key',
              'aws_session_token']:
        if env_vars.get(i.upper()):
            boto_args[i] = env_vars[i.upper()]
    return boto_args


def flatten_path_lists(env_dict, env_root=None):
    """Join paths in environment dict down to strings."""
    for (key, val) in env_dict.items():
        # Lists are presumed to be path components and will be turned back
        # to strings
        if isinstance(val, list):
            env_dict[key] = os.path.join(env_root, os.path.join(*val)) if (env_root and not os.path.isabs(os.path.join(*val))) else os.path.join(*val)  # noqa pylint: disable=line-too-long
    return env_dict


def merge_nested_environment_dicts(env_dicts, env_name=None, env_root=None):
    """Return single-level dictionary from dictionary of dictionaries."""
    # If the provided dictionary is just a single "level" (no nested
    # environments), it applies to all environments
    if all(isinstance(val, (six.string_types, list))
           for (_key, val) in env_dicts.items()):
        return flatten_path_lists(env_dicts, env_root)

    if env_name is None:
        if env_dicts.get('*'):
            return flatten_path_lists(env_dicts.get('*'), env_root)
        return {}

    if not env_dicts.get('*') and not env_dicts.get(env_name):
        return {}

    combined_dicts = merge_dicts(env_dicts.get('*', {}),
                                 env_dicts.get(env_name, {}))
    return flatten_path_lists(combined_dicts, env_root)


def find_cfn_output(key, outputs):
    """Return CFN output value."""
    for i in outputs:
        if i['OutputKey'] == key:
            return i['OutputValue']
    return None


def get_embedded_lib_path():
    """Return path of embedded libraries."""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'embedded'
    )


def get_hash_for_filename(filename, hashfile_path):
    """Return hash for filename in the hashfile."""
    filehash = ''
    with open(hashfile_path, 'r') as stream:
        for _cnt, line in enumerate(stream):
            if line.rstrip().endswith(filename):
                filehash = re.match(r'^[A-Za-z0-9]*', line).group(0)
                break
    if filehash:
        return filehash
    raise AttributeError("Filename %s not found in hash file" % filename)


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

    Similar issues arise when calling python apps like pipenv that will have
    a windows-only suffix applied to them
    """
    fully_qualified_cmd_path = which(commands[0])
    if fully_qualified_cmd_path:
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
            failed_to_find_error = "Attempted to run \"%s\" and failed to find it (are you sure it is installed and added to your PATH?)" % command_list[0]  # noqa pylint: disable=line-too-long
            if sys.version_info[0] < 3:
                # Legacy exception version for python 2
                try:
                    check_call(command_list, env=env)
                except OSError:
                    print(failed_to_find_error, file=sys.stderr)
                    sys.exit(1)
            else:
                try:
                    check_call(command_list, env=env)
                # The noqa/pylint overrides can be dropped alongside python 2
                except FileNotFoundError:  # noqa pylint: disable=undefined-variable
                    print(failed_to_find_error, file=sys.stderr)
                    sys.exit(1)


def md5sum(filename):
    """Return MD5 hash of file."""
    md5 = hashlib.md5()
    with open(filename, 'rb') as stream:
        while True:
            data = stream.read(65536)  # 64kb chunks
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


def sha256sum(filename):
    """Return SHA256 hash of file."""
    sha256 = hashlib.sha256()
    mem_view = memoryview(bytearray(128 * 1024))
    with open(filename, 'rb', buffering=0) as stream:
        for i in iter(lambda: stream.readinto(mem_view), 0):
            sha256.update(mem_view[:i])
    return sha256.hexdigest()


def strip_leading_option_delim(args):
    """Remove leading -- if present.

    Using the "--" end of options syntax bypasses docopt's parsing of options.
    """
    if len(args) > 1:
        if args[0] == '--':
            return args[1:]
    return args


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
    """Mimic 'which' command behavior."""
    def is_exe(fpath):
        """Determine if program exists and is executable."""
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    def get_extensions():
        """Get PATHEXT if the exist, otherwise use default."""
        exts = ['.COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC']

        if os.environ.get('PATHEXT', []):
            exts = os.environ['PATHEXT']

        return exts.split(';')

    fname, file_ext = os.path.splitext(program)
    fpath, fname = os.path.split(program)

    if not file_ext and platform.system().lower() == 'windows':
        fnames = [fname + ext for ext in get_extensions()]
    else:
        fnames = [fname]

    for i in fnames:
        if fpath:
            exe_file = os.path.join(fpath, i)
            if is_exe(exe_file):
                return exe_file
        else:
            for path in os.environ.get('PATH').split(os.pathsep) if 'PATH' in os.environ else [os.getcwd()]:  # noqa pylint: disable=line-too-long
                exe_file = os.path.join(path, i)
                if is_exe(exe_file):
                    return exe_file

    return None
