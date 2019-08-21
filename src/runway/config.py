"""Runway config file module."""
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union, Iterator  # pylint: disable=unused-import
import yaml

LOGGER = logging.getLogger('runway')


class ConfigComponent(object):
    """Base class for runway config components."""

    def get(self, key, default=None):
        # type: (str, Any) -> Any
        """Implement evaluation of get."""
        return getattr(self, key, getattr(self, key.replace('-', '_'), default))

    def __getitem__(self, key):
        # type: (str) -> Any
        """Implement evaluation of self[key]."""
        return getattr(self, key, getattr(self, key.replace('-', '_')))

    def __setitem__(self, key, value):
        # type: (str, Any) -> None
        """Implement evaluation of self[key] for assignment."""
        setattr(self, key, value)

    def __len__(self):
        # type: () -> int
        """Implement the built-in function len()."""
        return len(self.__dict__)

    def __iter__(self):
        # type: () -> Iterator[Any]
        """Return iterator object that can iterate over all attributes."""
        return iter(self.__dict__)


class ModuleDefinition(ConfigComponent):
    """Items in the modules definition block of a deployment."""

    def __init__(self,
                 name,  # type: str
                 path,  # type: str
                 environments=None,  # type: Optional[Dict[str, Dict[str, Any]]]
                 options=None  # type: Optional[Dict[str, Any]]
                 # pylint only complains for python2
                 ):  # pylint: disable=bad-continuation
        # type: (...) -> None
        """Runway module definition.

        Args:
            name (str): Name of the module. Used to easily parse logs.
            path (str): Path to the module.
            environments (Optional[Dict[str, Dict[str, Any]]]): Mapping for
                variables to environment names. When run, the variables
                defined here are merged with those in the .env file. If
                this is defined, the .env files can be omitted.
            options (Optional[Dict[str, Any]]): Module specific options.
                See the Module Configurations section of the docs for more
                details.

        """
        self.name = name
        self.path = path
        self.environments = environments
        self.options = options

    @classmethod
    def from_list(cls, modules):
        """Instantiate ModuleDefinition from a list."""
        results = []
        for mod in modules:
            if isinstance(mod, str):
                results.append(cls(mod, mod, {}))
                continue
            results.append(cls(mod.get('name', mod['path']),
                               mod['path'], mod.get('environments', {}),
                               mod.get('options', {})))
        return results


class DeploymentDefinition(ConfigComponent):  # pylint: disable=too-many-instance-attributes
    """Items in the deployments definition block of a runway config."""

    def __init__(self, deployment):
        # type: (Dict[str, Any]) -> None
        """Runway deployment definition.

        Arguments are read from a dict for initialization. All dashes are
        converted to underscores when being added as attributes.

        Args:
            account-alias (Optional[Dict[str, str]]): A mapping of
                'environment: alias' that, if provided, is used to very
                the currently assumed role or credentials.
            account-id (Optional[Dict[str, Union[str, int]]]): A mapping of
                'environment: id' that, if provided, is used to very
                the currently assumed role or credentials.
            assume-role (Optional[Dict[str, Union[str, Dict[str, str]]]]):
                A mapping of 'environment: role' or
                'environment: {arn: role, duration: int}' to assume a role
                when processing a deployment. 'arn: role' can be used to apply
                the same role to all environment. 'post_deploy_env_revert: true'
                can also be provided to revert credentials to their original
                after processing.
            current_dir (bool): Used to deploy the module in which the runway
                config file is located.
            environments (Optional[Dict[str, Dict[str, Any]]]): Mapping for
                variables to environment names. When run, the variables
                defined here are merged with those in the .env file and
                environments section of each modules.
            env_vars (Optional[Dict[str, Dict[str, Any]]]): A mapping of
                OS environment variable overrides to apply when processing
                modules in the deployment. Can be defined per environment or
                for all environments.
            modules (List[Dict[str, Any]]): The modules to be processed in
                order of definition.
            module_options (Dict[str, Any]): Options that are shared among all
                modules in the deployment.
            name (str): Name of the deployment. Used to easily parse logs.
            regions (List[str]): AWS regions where modules will be applied.
            skip-npm-ci (bool): Should rarely be used. Omits npm ci
                execution during Serverless deployments. (i.e. for use with
                pre-packaged node_modules)

        """
        self.account_alias = deployment.get(
            'account-alias', {}
        )  # type: Optional[Dict[str, str]]
        self.account_id = deployment.get(
            'account-id', {}
        )  # type: Optional[Dict[str, Union[str, int]]]
        self.assume_role = deployment.get(
            'assume-role', {}
        )  # type: Optional[Dict[str, Union[str, Dict[str, str]]]]
        self.current_dir = deployment.get('current_dir', False)  # type: bool
        self.environments = deployment.get(
            'environments', {}
        )  # type: Optional[Dict[str, Dict[str, Any]]]
        self.env_vars = deployment.get(
            'env_vars', {}
        )  # type: Optional[Dict[str, Dict[str, Any]]]
        self.modules = ModuleDefinition.from_list(
            deployment['modules']
        )  # type: List[ModuleDefinition]
        self.module_options = deployment.get(
            'module_options', {}
        )  # type: Optional(Dict[str, Any])
        self.name = deployment['name']  # type: str
        self.regions = deployment.get('regions', [])  # type: List[str]
        self.skip_npm_ci = deployment.get('skip-npm-ci', False)  # type: bool

    @classmethod
    def from_list(cls, deployments):
        """Instantiate DeploymentDefinitions from a list."""
        results = []
        for i, deployment in enumerate(deployments):
            if not deployment.get('name'):
                deployment['name'] = 'deployment_{}'.format(str(i + 1))
            results.append(cls(deployment))
        return results


class TestDefinition(ConfigComponent):
    """Item in the tests definition block of a runway config."""

    def __init__(self,
                 name,  # type: str
                 test_type,  # type: str
                 args=None,  # type: Optional[Dict[str, Any]]
                 required=True  # type: bool
                 # pylint only complains for python2
                 ):  # pylint: disable=bad-continuation
        # type: (...) -> None
        """Runway test definition.

        Args:
            name (str): Can be used to describe the test for debugging.
            type (str): The type of test to run.
            args (Dict[str, Any]): Arguments to be passed to the test. Defining
                arguments is implimented in the test itself.
            required (bool):  If false, testing will continue if the test fails.

        """
        self.name = name
        self.type = test_type
        self.args = args
        self.required = required

    @classmethod
    def from_list(cls, tests):
        # type: (List[Dict[str, Any]]) -> List[TestDefinition]
        """Instantiate TestDefinitions from a list."""
        return [cls(t.get('name', 'test_{}'.format(i + 1)),
                    t['type'], t.pop('args', {}),
                    t.get('required', True))
                for i, t in enumerate(tests)]


class Config(ConfigComponent):
    """Runway config."""

    accepted_names = ['runway.yml', 'runway.yaml']

    def __init__(self,
                 deployments,  # type: List[Dict[str, Any]]
                 tests=None,  # type: List[Dict[str, Any]]
                 ignore_git_branch=False  # type: bool
                 # pylint only complains for python2
                 ):  # pylint: disable=bad-continuation
        # type: (...) -> None
        """Runway config.

        Args:
            deployments (List[Dict[str, Any]]): Deployment definitions
                in raw format that will be instantiated into the appropriate
                class.
            tests (List[Dict[str, Any]]): Test definitions in raw format
                that will be instantiated into the appropriate class.
            ignore_git_branch (bool): Disable git branch lookup when
                using environment folders, Mercurial, or defining the
                DEPLOY_ENVIRONMENT environment variable before execution.

        """
        self.deployments = DeploymentDefinition.from_list(deployments)
        self.tests = TestDefinition.from_list(tests)
        self.ignore_git_branch = ignore_git_branch

    @classmethod
    def load_from_file(cls, config_path):
        # type: (str) -> Config
        """Load config file into a Config object."""
        if not os.path.isfile(config_path):
            LOGGER.error("Runway config file was not found (looking for "
                         "%s)",
                         config_path)
            sys.exit(1)
        with open(config_path) as data_file:
            config_file = yaml.safe_load(data_file)
            return Config(config_file['deployments'],
                          config_file.get('tests', []),
                          config_file.get('ignore_git_branch', False))

    @classmethod
    def find_config_file(cls, config_dir=None):
        # type: (Optional[str]) -> str
        """Find the runway config file."""
        if not config_dir:
            config_dir = os.getcwd()

        for name in cls.accepted_names:
            conf_path = os.path.join(config_dir, name)
            if os.path.isfile(conf_path):
                return conf_path

        LOGGER.error('Runway config file was not found. Looking for one '
                     'of %s in %s', str(cls.accepted_names), config_dir)
        sys.exit(1)
