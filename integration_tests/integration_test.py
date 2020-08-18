"""Integration test module."""
import errno
import os
import shutil
import subprocess
import sys
from copy import deepcopy

import yaml
from send2trash import send2trash

from runway.util import change_dir


class IntegrationTest(object):
    """Base class for Integration Tests.

    Attributes:
        REQUIRED_FIXTURE_FILES (List[str]): List of fixture files that
            will be copied to the current ``working_dir`` from
            ``fixture_dir`` when using the ``copy_fixtures`` method.
        fixture_dir (str): Path to ``fixture`` directory relative to
            ``working_dir``.
        tests_dir (str): Path to ``tests`` directory relative to
            ``working_dir``.
        working_dir (str): Path that the test is running in.

    """

    REQUIRED_FIXTURE_FILES = []

    def __init__(self, logger, env_vars=None):
        """Initialize base class."""
        self.logger = logger
        self.environment = deepcopy(env_vars or os.environ)
        self.runway_config_path = None
        # roundabout way to get the file path of a subclass
        self.working_dir = os.path.abspath(
            os.path.dirname(sys.modules[self.__module__].__file__)
        )
        self.fixture_dir = os.path.join(self.working_dir, "fixtures")
        self.tests_dir = os.path.join(self.working_dir, "tests")

    @property
    def deploy_env(self):
        """Return DEPLOY_ENVIRONMENT for the test."""
        return self.environment.get("DEPLOY_ENVIRONMENT")

    @deploy_env.setter
    def deploy_env(self, value):
        """Set the DEPLOY_ENVIRONMENT value."""
        self.logger.info('Setting "DEPLOY_ENVIRONMENT" to "%s"', value)
        self.environment["DEPLOY_ENVIRONMENT"] = value

    @property
    def region(self):
        """Return the region set for the test environment."""
        return self.environment.get(
            "AWS_DEFAULT_REGION", self.environment.get("AWS_REGION", "us-east-1")
        )

    @region.setter
    def region(self, value):
        """Set the value of region."""
        self.environment["AWS_DEFAULT_REGION"] = value
        self.environment["AWS_REGION"] = value

    def copy_fixtures(self):
        """Copy fixtures to the root of the tests dir."""
        self.logger.info(
            "Fixtures defined for tests: %s", str(self.REQUIRED_FIXTURE_FILES)
        )
        for fixture in self.REQUIRED_FIXTURE_FILES:
            src = os.path.join(self.fixture_dir, fixture)
            dest = os.path.join(self.working_dir, fixture)
            if os.path.isfile(src):
                self.logger.info('Copying "%s" to "%s"...', src, dest)
                shutil.copy(src, dest)

    def cleanup_fixtures(self):
        """Delete copied fixtures."""
        for fixture in self.REQUIRED_FIXTURE_FILES:
            fixture_path = os.path.join(self.working_dir, fixture)
            self.logger.info('Deleting "%s"...', fixture_path)
            try:
                send2trash(fixture_path)
            except OSError as err:
                if err.errno == errno.ENOENT or "not found" in str(err):
                    continue
                raise

    def parse_config(self, path):
        """Read and parse yml."""
        if not os.path.isfile(path):
            self.logger.error('Config file was not found (looking for "%s")', path)
        with open(path) as data_file:
            return yaml.safe_load(data_file)

    def runway_cmd(self, action, *args, env_vars=None, tags=None, timeout=900):
        """Run a deploy command based on tags.

        Args:
            action (str): Runway action. (e.g. ``deploy``, ``destroy``)
            env_vars (Optional[Dict[str, str]]): Can be used to override
                environment variables for the invocation.
            tags (Optional[List[str]]): List of tag options to pass to Runway.
            timeout (int): Seconds to wait for process to complete.
            args (str): Additional arguments to add to the command. These
                are places after any ``--tag`` options.

        Returns:
            Tuple[int, str, str]: The return code, ``stdout``, and ``stderr``
            of the process.

        """
        cmd = ["runway", action]
        if tags:
            for tag in tags:
                cmd.extend(["--tag", tag])
        cmd.extend(args)
        self.logger.info("Running command: %s", str(cmd))
        with change_dir(self.working_dir):
            cmd_process = subprocess.Popen(
                cmd,
                env=env_vars or self.environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            stdout, stderr = cmd_process.communicate(timeout=timeout)
            print(stderr)
        return cmd_process.returncode, stdout, stderr

    def set_environment(self, env):
        """Set deploy environment."""
        if isinstance(env, str):
            self.deploy_env = env

    def set_env_var(self, var_name, var):
        """Set an environment variable."""
        self.logger.info('Setting "%s" to "%s"', var_name, var)
        if not isinstance(var, dict):
            env = {var_name: var}
        self.environment.update(env)

    def unset_env_var(self, var):
        """Unset environment variable."""
        self.logger.info('Unsetting "%s" Environment Variable', var)
        del self.environment[var]

    def run(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError("You must implement the run() method " "yourself!")

    def teardown(self):
        """Implement dummy method (set in consuming classes)."""
        raise NotImplementedError(
            "You must implement the teardown() method " "yourself!"
        )
