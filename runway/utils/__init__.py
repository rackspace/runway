"""Utility functions."""

from __future__ import annotations

import hashlib
import importlib
import json
import logging
import os
import platform
import re
import stat
import sys
from collections.abc import Iterable, Iterator, MutableMapping
from contextlib import AbstractContextManager, contextmanager
from functools import cached_property  # noqa: F401  # TODO (kyle): remove in next major release
from pathlib import Path
from subprocess import check_call
from typing import TYPE_CHECKING, Any, Callable, cast, overload

import yaml
from pydantic import BaseModel as _BaseModel

# make this importable without defining __all__ yet.
# more things need to be moved of this file before starting an explicit __all__.
from . import pydantic_validators  # noqa: F401
from ._file_hash import FileHash  # noqa: F401
from ._json_encoder import JsonEncoder  # noqa: F401
from ._version import Version  # noqa: F401

if TYPE_CHECKING:
    from types import TracebackType

    from mypy_boto3_cloudformation.type_defs import OutputTypeDef
    from typing_extensions import Literal

    from ..compat import Self

AWS_ENV_VARS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
DOC_SITE = "https://runway.readthedocs.io"
EMBEDDED_LIB_PATH = str(Path(__file__).resolve().parent / "embedded")

LOGGER = logging.getLogger(__name__)


class BaseModel(_BaseModel):
    """Base class for Runway models."""

    def get(self, name: str, default: Any = None) -> Any:
        """Safely get the value of an attribute.

        Args:
            name: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        return getattr(self, name, default)

    def __contains__(self, name: object) -> bool:
        """Implement evaluation of 'in' conditional.

        Args:
            name: The name to check for existence in the model.

        """
        if name in self.__dict__:
            return True
        # extra files are no longer added to __dict__, they are placed in `model_extra`
        return bool(self.model_extra and name in self.model_extra)

    def __getitem__(self, name: str) -> Any:
        """Implement evaluation of self[name].

        Args:
            name: Attribute name to return the value for.

        Returns:
            The value associated with the provided name/attribute name.

        Raises:
            AttributeError: If attribute does not exist on this object.

        """
        return getattr(self, name)

    def __setitem__(self, name: str, value: Any) -> None:
        """Implement item assignment (e.g. ``self[name] = value``).

        Args:
            name: Attribute name to set.
            value: Value to assign to the attribute.

        """
        super().__setattr__(name, value)


class MutableMap(MutableMapping[str, Any]):
    """Base class for mutable map objects."""

    def __init__(self, **kwargs: Any) -> None:
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
    def data(self) -> dict[str, Any]:
        """Sanitized output of __dict__.

        Removes anything that starts with ``_``.

        """
        result: dict[str, Any] = {}
        for key, val in self.__dict__.items():
            if key.startswith("_"):
                continue
            result[key] = val.data if isinstance(val, MutableMap) else val
        return result

    def clear_found_cache(self) -> None:
        """Clear _found_cache."""
        for val in self.__dict__.values():
            if isinstance(val, MutableMap):
                val.clear_found_cache()
        if hasattr(self, "_found_queries"):
            self._found_queries.clear()

    def find(self, query: str, default: Any = None, ignore_cache: bool = False) -> Any:
        """Find a value in the map.

        Previously found queries are cached to increase search speed. The
        cached value should only be used if values are not expected to change.

        Args:
            query: A period delimited string that is split to search for
                nested values
            default: The value to return if the query was unsuccessful.
            ignore_cache: Ignore cached value.

        """
        if not hasattr(self, "_found_queries"):
            # if not created from kwargs, this attr won't exist yet
            # this is done to prevent endless recursion
            self._found_queries = MutableMap()

        if not ignore_cache:
            cached_result = self._found_queries.get(query, None)
            if cached_result:
                return cached_result

        split_query = query.split(".")

        if len(split_query) == 1:
            result = self.get(split_query[0], default)
            if result != default:
                self._found_queries[split_query[0]] = result
            return result

        nested_value = self.get(split_query[0])

        if not nested_value:
            if self.get(query):
                return self.get(query)
            return default

        nested_value = nested_value.find(split_query[1])

        try:
            nested_value = self[split_query[0]].find(
                query=".".join(split_query[1:]),
                default=default,
                ignore_cache=ignore_cache,
            )
            if nested_value != default:
                self._found_queries[query] = nested_value
            return nested_value
        except (AttributeError, KeyError):
            return default

    def get(self, key: str, default: Any = None) -> Any:
        """Implement evaluation of self.get.

        Args:
            key: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        return getattr(self, key, default)

    def __bool__(self) -> bool:
        """Implement evaluation of instances as a bool."""
        return bool(self.data)

    def __contains__(self, value: Any) -> bool:
        """Implement evaluation of 'in' conditional."""
        return value in self.data

    def __getitem__(self, key: str) -> Any:
        """Implement evaluation of self[key].

        Args:
            key: Attribute name to return the value for.

        Returns:
            The value associated with the provided key/attribute name.

        Raises:
            AttributeError: If attribute does not exist on this object.

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                print(obj['key'])
                # value

        """
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
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

    def __delitem__(self, key: str) -> None:
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

    def __len__(self) -> int:
        """Implement the built-in function len().

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                print(len(obj))
                # 1

        """
        return len(self.__dict__)

    def __iter__(self) -> Iterator[Any]:
        """Return iterator object that can iterate over all attributes.

        Example:
            .. codeblock: python

                obj = MutableMap(**{'key': 'value'})
                for k, v in obj.items():
                    print(f'{key}: {value}')
                # key: value

        """
        return iter(self.__dict__)

    def __str__(self) -> str:
        """Return string representation of the object."""
        return json.dumps(self.data, default=json_serial)


class SafeHaven(AbstractContextManager["SafeHaven"]):
    """Context manager that caches and resets important values on exit.

    Caches and resets os.environ, sys.argv, sys.modules, and sys.path.

    """

    def __init__(
        self,
        argv: Iterable[str] | None = None,
        environ: dict[str, str] | None = None,
        sys_modules_exclude: Iterable[str] | None = None,
        sys_path: Iterable[str] | None = None,
    ) -> None:
        """Instantiate class.

        Args:
            argv: Override the value of sys.argv.
            environ: Update os.environ.
            sys_modules_exclude: A list of modules to exclude when reverting
                sys.modules to its previous state.
                These are checked as ``module.startswith(name)``.
            sys_path: Override the value of sys.path.

        """
        self.__os_environ = dict(os.environ)
        self.__sys_argv = list(sys.argv)
        # deepcopy can't pickle sys.modules and dict()/.copy() are not safe
        self.__sys_modules = {}
        for k, v in sys.modules.items():
            self.__sys_modules[k] = v
        self.__sys_path = list(sys.path)
        # more informative origin for log statements
        self.logger = logging.getLogger("runway." + self.__class__.__name__)
        self.sys_modules_exclude: set[str] = (
            set(sys_modules_exclude) if sys_modules_exclude else set()
        )
        self.sys_modules_exclude.add("runway")

        if isinstance(argv, list):
            sys.argv = argv
        if isinstance(environ, dict):
            os.environ.update(environ)
        if isinstance(sys_path, list):
            sys.path = sys_path

    def reset_all(self) -> None:
        """Reset all values cached by this context manager."""
        self.logger.debug("resetting all managed values...")
        self.reset_os_environ()
        self.reset_sys_argv()
        self.reset_sys_modules()
        self.reset_sys_path()

    def reset_os_environ(self) -> None:
        """Reset the value of os.environ."""
        self.logger.debug("resetting os.environ: %s", json.dumps(self.__os_environ))
        os.environ.clear()
        os.environ.update(self.__os_environ)

    def reset_sys_argv(self) -> None:
        """Reset the value of sys.argv."""
        self.logger.debug("resetting sys.argv: %s", json.dumps(self.__sys_argv))
        sys.argv = self.__sys_argv

    def reset_sys_modules(self) -> None:
        """Reset the value of sys.modules."""
        self.logger.debug("resetting sys.modules...")
        # sys.modules can be manipulated to force reloading modules but,
        # replacing it outright does not work as expected
        for module in list(sys.modules.keys()):
            if module not in self.__sys_modules and not any(
                module.startswith(n) for n in self.sys_modules_exclude
            ):
                self.logger.debug(
                    'removed sys.module: {"%s": "%s"}', module, sys.modules.pop(module)
                )

    def reset_sys_path(self) -> None:
        """Reset the value of sys.path."""
        self.logger.debug("resetting sys.path: %s", json.dumps(self.__sys_path))
        sys.path = self.__sys_path

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            SafeHaven: Instance of the context manager.

        """
        self.logger.debug("entering a safe haven...")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the context manager."""
        self.logger.debug("leaving the safe haven...")
        self.reset_all()


# TODO (kyle): remove after https://github.com/yaml/pyyaml/issues/234 is resolved
class YamlDumper(yaml.Dumper):
    """Custom YAML Dumper.

    This Dumper allows for YAML to be output to follow YAML spec 1.2,
    example 2.3 of collections (2.1). This provides an output that is more
    humanreadable and complies with yamllint.

    Example:
        >>> print(yaml.dump({'key': ['val1', 'val2']}, Dumper=YamlDumper))

    Note:
        YAML 1.2 Specification: https://yaml.org/spec/1.2/spec.html
        used for reference.

    """

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:  # noqa: ARG002
        """Override parent method."""
        return super().increase_indent(flow, False)


@contextmanager
def argv(*args: str) -> Iterator[None]:
    """Context manager for temporarily changing sys.argv."""
    original_argv = sys.argv.copy()
    try:
        sys.argv = list(args)  # convert tuple to list
        yield
    finally:
        # always restore original value
        sys.argv = original_argv


@contextmanager
def change_dir(newdir: Path | str) -> Iterator[None]:
    """Change directory.

    Adapted from http://stackoverflow.com/a/24176022

    Args:
        newdir: Path to change directory into.

    """
    prevdir = Path.cwd().resolve()
    if isinstance(newdir, str):
        newdir = Path(newdir)
    os.chdir(newdir.resolve())
    try:
        yield
    finally:
        os.chdir(prevdir)


def ensure_file_is_executable(path: str) -> None:
    """Exit if file is not executable.

    Args:
        path: Path to file.

    Raises:
        SystemExit: file is not executable.

    """
    if platform.system() != "Windows" and (not stat.S_IXUSR & Path(path).stat()[stat.ST_MODE]):
        print(f"Error: File {path} is not executable")  # noqa: T201
        sys.exit(1)


def ensure_string(value: Any) -> str:
    """Ensure value is a string."""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode()
    raise TypeError(f"Expected str or bytes but received {type(value)}")


@contextmanager
def environ(env: dict[str, str] | None = None, **kwargs: str) -> Iterator[None]:
    """Context manager for temporarily changing os.environ.

    The original value of os.environ is restored upon exit.

    Args:
        env: Dictionary to use when updating os.environ.
        **kwargs: Arbitrary keyword arguments.

    """
    env = env or {}
    env.update(kwargs)

    original_env = dict(os.environ)
    os.environ.update(env)

    try:
        yield
    finally:
        # always restore original values
        os.environ.clear()
        os.environ.update(original_env)


def json_serial(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, MutableMap):
        return obj.data
    raise TypeError(f"Type {type(obj)} not serializable")


def load_object_from_string(fqcn: str, try_reload: bool = False) -> type | Callable[..., Any]:
    """Convert "." delimited strings to a python object.

    Args:
        fqcn: A "." delimited string representing the full path to an
            object (function, class, variable) inside a module
        try_reload: Try to reload the module so any global variables
            set within the file during import are reloaded. This only applies
            to modules that are already imported and are not builtin.

    Returns:
        Object being imported from the provided path.

    Example::

        load_object_from_string("os.path.basename")
        load_object_from_string("logging.Logger")
        load_object_from_string("LocalClassName")

    """
    module_path = "__main__"
    object_name = fqcn
    if "." in object_name:
        module_path, object_name = fqcn.rsplit(".", 1)
        if (
            try_reload
            and sys.modules.get(module_path)
            and module_path.split(".")[0] not in sys.builtin_module_names  # skip builtins
        ):
            importlib.reload(sys.modules[module_path])
        else:
            importlib.import_module(module_path)
    return getattr(sys.modules[module_path], object_name)


@overload
def merge_dicts(
    dict1: dict[Any, Any], dict2: dict[Any, Any], deep_merge: bool = ...
) -> dict[str, Any]: ...


@overload
def merge_dicts(dict1: list[Any], dict2: list[Any], deep_merge: bool = ...) -> list[Any]: ...


def merge_dicts(
    dict1: dict[Any, Any] | list[Any],
    dict2: dict[Any, Any] | list[Any],
    deep_merge: bool = True,
) -> dict[Any, Any] | list[Any]:
    """Merge dict2 into dict1."""
    if deep_merge:
        if isinstance(dict1, list) and isinstance(dict2, list):
            return dict1 + dict2

        if not isinstance(dict1, dict) or not isinstance(dict2, dict):
            return dict2

        for key in dict2:
            dict1[key] = merge_dicts(dict1[key], dict2[key], True) if key in dict1 else dict2[key]
        return dict1
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        dict3 = dict1.copy()
        dict3.update(dict2)
        return dict3
    raise ValueError(f"values of type {type(dict1)} and {type(dict2)} must be type dict")


def snake_case_to_kebab_case(value: str) -> str:
    """Convert snake_case to kebab-case.

    Args:
        value: The string value to convert.

    """
    return value.replace("_", "-")


def extract_boto_args_from_env(env_vars: dict[str, str]) -> dict[str, str]:
    """Return boto3 client args dict with environment creds."""
    return {
        i: env_vars[i.upper()]
        for i in ["aws_access_key_id", "aws_secret_access_key", "aws_session_token"]
        if env_vars.get(i.upper(), "")
    }


def flatten_path_lists(env_dict: dict[str, Any], env_root: str | None = None) -> dict[str, Any]:
    """Join paths in environment dict down to strings."""
    for key, val in env_dict.items():
        # Lists are presumed to be path components and will be turned back
        # to strings
        if isinstance(val, list):
            env_dict[key] = (
                Path(env_root).joinpath(*cast("list[str]", val))
                if (env_root and not Path(*cast("list[str]", val)).is_absolute())
                else Path(*cast("list[str]", val))
            )
    return env_dict


def merge_nested_environment_dicts(
    env_dicts: dict[str, Any],
    env_name: str | None = None,
    env_root: str | None = None,
) -> dict[str, Any]:
    """Return single-level dictionary from dictionary of dictionaries."""
    # If the provided dictionary is just a single "level" (no nested
    # environments), it applies to all environments
    if all(isinstance(val, (str, list)) for (_key, val) in env_dicts.items()):
        return flatten_path_lists(env_dicts, env_root)

    if env_name is None:
        if env_dicts.get("*"):
            return flatten_path_lists(env_dicts.get("*", {}), env_root)
        return {}

    if not env_dicts.get("*") and not env_dicts.get(env_name):
        return {}

    combined_dicts = merge_dicts(
        cast("dict[Any, Any]", env_dicts.get("*", {})),
        cast("dict[Any, Any]", env_dicts.get(env_name, {})),
    )
    return flatten_path_lists(combined_dicts, env_root)


def find_cfn_output(key: str, outputs: list[OutputTypeDef]) -> str | None:
    """Return CFN output value.

    Args:
        key: Name of the output.
        outputs: List of Stack outputs.

    """
    for i in outputs:
        if i.get("OutputKey") == key:
            return i.get("OutputValue")
    return None


def get_embedded_lib_path() -> str:
    """Return path of embedded libraries."""
    return str(Path(__file__).resolve().parent / "embedded")


def get_hash_for_filename(filename: str, hashfile_path: str) -> str:
    """Return hash for filename in the hashfile."""
    filehash = ""
    with open(hashfile_path, encoding="utf-8") as stream:  # noqa: PTH123
        for _cnt, line in enumerate(stream):
            if line.rstrip().endswith(filename):
                match = re.match(r"^[A-Za-z0-9]*", line)
                if match:
                    filehash = match.group(0)
                    break
    if filehash:
        return filehash
    raise AttributeError(f"Filename {filename} not found in hash file")


@contextmanager
def ignore_exit_code_0() -> Iterator[None]:
    """Capture exit calls and ignore those with exit code 0."""
    try:
        yield
    except SystemExit as exit_exc:
        if exit_exc.code != 0:
            raise


def fix_windows_command_list(commands: list[str]) -> list[str]:
    """Return command list with working Windows commands.

    npm on windows is npm.cmd, which will blow up
    subprocess.check_call(['npm', '...'])

    Similar issues arise when calling python apps that will have a windows-only
    suffix applied to them.

    """
    fully_qualified_cmd_path = which(commands[0])
    if fully_qualified_cmd_path:
        commands[0] = Path(fully_qualified_cmd_path).name
    return commands


def run_commands(
    commands: list[dict[str, list[str] | str] | list[str] | str],
    directory: Path | str,
    env: dict[str, str] | None = None,
) -> None:
    """Run list of commands."""
    directory = Path(directory)
    if env is None:
        env = os.environ.copy()
    for step in commands:
        if isinstance(step, (list, str)):
            execution_dir = directory
            raw_command = step
        elif step.get("command"):  # dictionary
            execution_dir = (
                directory / str(step["cwd"]) if step.get("cwd") and step["cwd"] else directory
            )
            raw_command = step["command"]
        else:
            raise AttributeError(f"Invalid command step: {step}")
        command_list = raw_command.split(" ") if isinstance(raw_command, str) else raw_command
        if platform.system().lower() == "windows":
            command_list = fix_windows_command_list(command_list)

        with change_dir(execution_dir):
            failed_to_find_error = (
                f'Attempted to run "{command_list[0]}" and failed to find it (are you sure it is '
                "installed and added to your PATH?)"
            )
            try:
                check_call(command_list, env=env)
            except FileNotFoundError:
                print(failed_to_find_error, file=sys.stderr)  # noqa: T201
                sys.exit(1)


def get_file_hash(
    filename: str,
    algorithm: Literal[
        "blake2b",
        "blake2b",
        "md5",
        "sha1",
        "sha224",
        "sha256",
        "sha3_224",
        "sha3_256",
        "sha3_384",
        "sha3_512",
        "sha384",
        "sha512",
        "shake_128",
        "shake_256",
    ],
) -> str:
    """Return cryptographic hash of file.

    .. deprecated:: 2.4.0
        Use :class:`runway.utils.FileHash` instead.

    """
    LOGGER.warning(
        "%s.get_file_hash is deprecated and will be removed in the next major release",
        __name__,
    )
    file_hash = getattr(hashlib, algorithm)()
    with open(filename, "rb") as stream:  # noqa: PTH123
        while True:
            data = stream.read(65536)  # 64kb chunks
            if not data:
                break
            file_hash.update(data)
    return file_hash.hexdigest()


def md5sum(filename: str) -> str:
    """Return MD5 hash of file.

    .. deprecated:: 2.4.0
        Use :class:`runway.utils.FileHash` instead.

    """
    LOGGER.warning(
        "%s.md5sum is deprecated and will be removed in the next major release",
        __name__,
    )
    return get_file_hash(filename, "md5")


def sha256sum(filename: str) -> str:
    """Return SHA256 hash of file.

    .. deprecated:: 2.4.0
        Use :class:`runway.utils.FileHash` instead.

    """
    LOGGER.warning(
        "%s.sha256sum is deprecated and will be removed in the next major release",
        __name__,
    )
    sha256 = hashlib.sha256()
    with open(filename, "rb", buffering=0) as stream:  # noqa: PTH123
        mem_view = memoryview(bytearray(128 * 1024))
        for i in iter(lambda: stream.readinto(mem_view), 0):
            sha256.update(mem_view[:i])
    return sha256.hexdigest()


@contextmanager
def use_embedded_pkgs(embedded_lib_path: str | None = None) -> Iterator[None]:
    """Temporarily prepend embedded packages to sys.path."""
    if embedded_lib_path is None:
        embedded_lib_path = get_embedded_lib_path()

    old_sys_path = list(sys.path)
    sys.path.insert(1, embedded_lib_path)  # https://stackoverflow.com/a/10097543
    try:
        yield
    finally:
        sys.path = old_sys_path


def which(program: str) -> str | None:
    """Mimic 'which' command behavior."""

    def is_exe(fpath: str) -> bool:
        """Determine if program exists and is executable."""
        return Path(fpath).is_file() and os.access(fpath, os.X_OK)

    def get_extensions() -> list[str]:
        """Get PATHEXT if the exist, otherwise use default."""
        exts = ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC"

        if os.getenv("PATHEXT"):
            exts = os.environ["PATHEXT"]

        return exts.split(";")

    fname, file_ext = os.path.splitext(program)  # noqa: PTH122
    fpath, fname = os.path.split(program)

    if not file_ext and platform.system().lower() == "windows":
        fnames = [fname + ext for ext in get_extensions()]
    else:
        fnames = [fname]

    for i in fnames:
        if fpath:
            exe_file = os.path.join(fpath, i)  # noqa: PTH118
            if is_exe(exe_file):
                return exe_file
        else:
            for path in (
                os.environ.get("PATH", "").split(os.pathsep)
                if "PATH" in os.environ
                else [os.getcwd()]  # noqa: PTH109
            ):
                exe_file = os.path.join(path, i)  # noqa: PTH118
                if is_exe(exe_file):
                    return exe_file

    return None
