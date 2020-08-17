"""Runway module module."""
import logging
import os
import platform
import subprocess
import sys

import six

from ..util import merge_nested_environment_dicts, which

if sys.version_info[0] > 2:  # TODO remove after droping python 2
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__)
NPM_BIN = "npm.cmd" if platform.system().lower() == "windows" else "npm"
NPX_BIN = "npx.cmd" if platform.system().lower() == "windows" else "npx"


def format_npm_command_for_logging(command):
    """Convert npm command list to string for display to user."""
    if platform.system().lower() == "windows" and (
        command[0] == "npx.cmd" and command[1] == "-c"
    ):
        return 'npx.cmd -c "%s"' % " ".join(command[2:])
    return " ".join(command)


def generate_node_command(command, command_opts, path, logger=LOGGER):
    """Return node bin command list for subprocess execution."""
    if which(NPX_BIN):
        # Use npx if available (npm v5.2+)
        cmd_list = [NPX_BIN, "-c", "%s %s" % (command, " ".join(command_opts))]
    else:
        logger.debug("npx not found; falling back to invoking shell script directly")
        cmd_list = [os.path.join(path, "node_modules", ".bin", command)] + command_opts
    logger.debug("node command: %s", format_npm_command_for_logging(cmd_list))
    return cmd_list


def run_module_command(cmd_list, env_vars, exit_on_error=True, logger=LOGGER):
    """Shell out to provisioner command."""
    logger.debug("running command: %s", " ".join(cmd_list))
    if exit_on_error:
        try:
            subprocess.check_call(cmd_list, env=env_vars)
        except subprocess.CalledProcessError as shelloutexc:
            sys.exit(shelloutexc.returncode)
    else:
        subprocess.check_call(cmd_list, env=env_vars)


def use_npm_ci(path):
    """Return true if npm ci should be used in lieu of npm install."""
    # https://docs.npmjs.com/cli/ci#description
    with open(os.devnull, "w") as fnull:
        if (
            (
                os.path.isfile(os.path.join(path, "package-lock.json"))
                or os.path.isfile(os.path.join(path, "npm-shrinkwrap.json"))
            )
            and subprocess.call(
                [NPM_BIN, "ci", "-h"], stdout=fnull, stderr=subprocess.STDOUT
            )
            == 0
        ):
            return True
    return False


def run_npm_install(path, options, context, logger=LOGGER):
    """Run npm install/ci."""
    # Use npm ci if available (npm v5.7+)
    cmd = [NPM_BIN, "<place-holder>"]
    if context.no_color:
        cmd.append("--no-color")
    if options.get("options", {}).get("skip_npm_ci"):
        logger.info("skipped npm ci/npm install")
        return
    if context.env_vars.get("CI") and use_npm_ci(path):
        logger.info("running npm ci...")
        cmd[1] = "ci"
    else:
        logger.info("running npm install...")
        cmd[1] = "install"
    subprocess.check_call(cmd)


def warn_on_boto_env_vars(env_vars):
    """Inform user if boto-specific environment variables are in use."""
    # https://github.com/serverless/serverless/issues/2151#issuecomment-255646512
    if env_vars.get("AWS_DEFAULT_PROFILE") and not env_vars.get("AWS_PROFILE"):
        LOGGER.warning(
            "AWS_DEFAULT_PROFILE environment variable is set "
            "during use of nodejs-based module and AWS_PROFILE is "
            "not set -- you likely want to set AWS_PROFILE instead"
        )


class RunwayModule(object):
    """Base class for Runway modules."""

    def __init__(self, context, path, options=None):
        """Instantiate class.

        Args:
            context (Context): Runway context object.
            path (Union[str, Path]): Path to the module.
            options (Dict[str, Dict[str, Any]]): Everything in the module
                definition merged with applicable values from the deployment
                definition.

        """
        self.context = context
        self.logger = LOGGER
        self.path = str(path)
        self.options = {} if options is None else options
        if isinstance(path, Path):
            self.name = options.get("name", path.name)
        else:  # until we can replace path with a Path object here, handle str
            self.name = options.get("name", Path(path).name)

    # the rest of these 'abstract' methods must have names which match
    #  the commands defined in `cli.py`

    def plan(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError("You must implement the plan() method yourself!")

    def deploy(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError("You must implement the deploy() method yourself!")

    def destroy(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError("You must implement the destroy() method yourself!")

    def __getitem__(self, key):
        """Make the object subscriptable.

        Args:
            key (str): Attribute to get.

        Returns:
            Any

        """
        return getattr(self, key)


class RunwayModuleNpm(RunwayModule):  # pylint: disable=abstract-method
    """Base class for Runway modules that use npm."""

    # TODO we need a better name than "options" or pass in as kwargs
    def __init__(self, context, path, options=None):
        """Instantiate class.

        Args:
            context (Context): Runway context object.
            path (Union[str, Path]): Path to the module.
            options (Dict[str, Dict[str, Any]]): Everything in the module
                definition merged with applicable values from the deployment
                definition.

        """
        options = options or {}
        super(RunwayModuleNpm, self).__init__(context, path, options)
        del self.options  # remove the attr set by the parent class

        # potential future state of RunwayModule attributes in a future release
        self._raw_path = Path(options.pop("path")) if options.get("path") else None
        self.environments = options.pop("environments", {})
        self.options = options.pop("options", {})
        self.parameters = options.pop("parameters", {})
        self.path = path if isinstance(self.path, Path) else Path(self.path)

        for k, v in options.items():
            setattr(self, k, v)

        self.check_for_npm()  # fail fast
        warn_on_boto_env_vars(self.context.env_vars)

    def check_for_npm(self):
        """Ensure npm is installed and in the current path."""
        if not which("npm"):
            self.logger.error(
                '"npm" not found in path or is not executable; '
                "please ensure it is installed correctly"
            )
            sys.exit(1)

    def log_npm_command(self, command):
        """Log an npm command that is going to be run.

        Args:
            command (List[str]): List that will be passed into a subprocess.

        """
        self.logger.debug("node command: %s", format_npm_command_for_logging(command))

    def npm_install(self):
        """Run ``npm install``."""
        cmd = [NPM_BIN, "<place-holder>"]
        if self.context.no_color:
            cmd.append("--no-color")
        if self.options.get("skip_npm_ci"):
            self.logger.info("skipped npm ci/npm install")
            return
        if self.context.is_noninteractive and use_npm_ci(str(self.path)):
            self.logger.info("running npm ci...")
            cmd[1] = "ci"
        else:
            self.logger.info("running npm install...")
            cmd[1] = "install"
        subprocess.check_call(cmd)

    def package_json_missing(self):
        """Check for the existence for a package.json file in the module.

        Returns:
            bool: True if the file was not found.

        """
        if not (self.path / "package.json").is_file():
            self.logger.debug("module is missing package.json")
            return True
        return False


class ModuleOptions(
    six.moves.collections_abc.MutableMapping
):  # pylint: disable=no-member
    """Base class for Runway module options."""

    @staticmethod
    def merge_nested_env_dicts(data, env_name=None):
        """Merge nested env dicts.

        Args:
            data (Any): Data to try to merge.
            env_name (Optional[str]): Current environment.

        Returns:
            Any

        """
        if isinstance(data, (list, type(None), six.string_types)):
            return data
        if isinstance(data, dict):
            return {
                key: merge_nested_environment_dicts(value, env_name)
                for key, value in data.items()
            }
        raise TypeError(
            "expected type of list, NoneType, or str; " "got type %s" % type(data)
        )

    @classmethod
    def parse(cls, context, **kwargs):
        """Parse module options definition to extract usable options.

        Args:
            context (Context): Runway context object.

        """
        raise NotImplementedError

    def __delitem__(self, key):
        # type: (str) -> None
        """Implement deletion of self[key].

        Args:
            key: Attribute name to remove from the object.

        Example:
            .. codeblock: python

                obj = ModuleOptions(**{'key': 'value'})
                del obj['key']
                print(obj.__dict__)
                # {}

        """
        delattr(self, key)

    def __getitem__(self, key):
        """Implement evaluation of self[key].

        Args:
            key: Attribute name to return the value for.

        Returns:
            The value associated with the provided key/attribute name.

        Raises:
            KeyError: Key does not exist in the object.

        Example:
            .. codeblock: python

                obj = ModuleOptions(**{'key': 'value'})
                print(obj['key'])
                # value

        """
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        """Implement assignment to self[key].

        Args:
            key: Attribute name to associate with a value.
            value: Value of a key/attribute.

        Example:
            .. codeblock: python

                obj = ModuleOptions()
                obj['key'] = 'value'
                print(obj['key'])
                # value

        """
        setattr(self, key, value)

    def __len__(self):
        # type: () -> int
        """Implement the built-in function len().

        Example:
            .. codeblock: python

                obj = ModuleOptions(**{'key': 'value'})
                print(len(obj))
                # 1

        """
        return len(self.__dict__)

    def __iter__(self):
        """Return iterator object that can iterate over all attributes.

        Example:
            .. codeblock: python

                obj = ModuleOptions(**{'key': 'value'})
                for k, v in obj.items():
                    print(f'{key}: {value}')
                # key: value

        """
        return iter(self.__dict__)
