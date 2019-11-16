"""Runway config file module."""
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union, Iterator  # pylint: disable=unused-import
import yaml

LOGGER = logging.getLogger('runway')


class ConfigComponent(object):
    """Base class for Runway config components."""

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


class ModuleDefinition(ConfigComponent):  # pylint: disable=too-many-instance-attributes
    """A module defines the directory to be processed and applicable options.

    It can consist of `CloudFormation`_ (using `Stacker`_),
    `Terraform`_, `Serverless Framework`_, `AWS CDK`_, or `Kubernetes`_.
    It is recommended to place the appropriate extension on each directory
    for identification (but it is not required). See
    :ref:`Repo Structure<repo-structure>` for examples of a module
    directory structure.

    +------------------+-----------------------------------------------+
    | Suffix/Extension | IaC Tool/Framework                            |
    +==================+===============================================+
    | ``.cdk``         | `AWS CDK`_                                    |
    +------------------+-----------------------------------------------+
    | ``.cfn``         | `CloudFormation`_                             |
    +------------------+-----------------------------------------------+
    | ``.sls``         | `Serverless Framework`_                       |
    +------------------+-----------------------------------------------+
    | ``.tf``          | `Terraform`_                                  |
    +------------------+-----------------------------------------------+
    | ``.k8s``         | `Kubernetes`_                                 |
    +------------------+-----------------------------------------------+

    A module is only deployed if there is a corresponding env/config
    present. This can take the form of either a file in the module folder
    or the ``environments`` option being defined. The naming format
    varies per-module type. See
    :ref:`Module Configurations<module-configurations>` for acceptable
    env/config file name formats.

    Modules can be defined as a string or a mapping. The minimum
    requirement for a module is a string that is equal to the name of
    the module directory. Providing a string is the same as providing a
    value for ``path`` in a mapping definition.

    Example:
      .. code-block:: yaml

        deployments:
          - modules:
              - my-module.cfn  # this
              - path: my-module.cfn  # is the same as this

    Using a map to define a module provides the ability to specify
    per-module ``options``, environment values, tags, and even a custom
    class for processing the module. The options that can be used with
    each module vary. For detailed information about module-specific
    options, see :ref:`Module Configurations<module-configurations>`.

    Example:
      .. code-block:: yaml

        deployments:
          - modules:
              - name: my-module
                path: my-module.tf
                environments:
                  dev:
                    image_id: ami-1234
                tags:
                  - app:example
                  - my-tag
                options:
                  terraform_backend_config:
                    region: us-east-1
                  terraform_backend_cfn_outputs:
                    bucket: StackName::OutputName
                    dynamodb_table: StackName::OutputName

    One special map keyword, ``parallel``, indicates a list of child
    modules that will be executed in parallel (simultaneously) if the
    ``CI`` :ref:`environment variable is set<non-interactive-mode>`.

    Example:
      .. code-block:: yaml

        deployments:
          - modules:
            - backend.tf
            - parallel:
              - servicea.cfn  # any normal module option can be used here
              - path: serviceb.cfn
              - path: servicec.cfn
                environments:
                  dev:
                    count: 1
                  prod:
                    count: 3
            - frontend.tf

    (in that ^ example, backend.tf will be deployed, the services will be all
    be deployed simultaneously, followed by frontend.tf)

    """

    def __init__(self,  # pylint: disable=too-many-arguments
                 name,  # type: str
                 path,  # type: str
                 class_path=None,  # type: Optional[str]
                 environments=None,  # type: Optional[Dict[str, Dict[str, Any]]]
                 env_vars=None,  # type: Optional[Dict[str, Dict[str, Any]]]
                 options=None,  # type: Optional[Dict[str, Any]]
                 tags=None,  # type: Optional[Dict[str, str]]
                 child_modules=None  # type: Optional[List[Union[str, Dict[str, Any]]]]
                 # pylint only complains for python2
                 ):  # pylint: disable=bad-continuation
        # type: (...) -> None
        """.. Runway module definition.

        Keyword Args:
            name (str): Name of the module. Used to more easily identify
                where different modules begin/end in the logs.
            path (str): Path to the module relative to the Runway config
                file. This cannot be higher than the Runway config file.
            class_path (Optional[str]): Path to custom Runway module class.
                Also used for static site deployments. See
                :ref:`Module Configurations<module-configurations>` for
                detailed usage.
            environments (Optional[Dict[str, Dict[str, Any]]]): Mapping for
                variables to environment names. When run, the variables
                defined here are merged with those in the
                ``.env``/``.tfenv``/environment config file. If this is
                defined, ``.env`` files can be omitted and the module
                will still be processed.
            env_vars (Optional[Dict[str, Dict[str, Any]]]): A mapping of
                OS environment variable overrides to apply when processing
                modules in the deployment. Can be defined per environment
                or for all environments using ``"*"`` as the environment
                name. Takes precendence over values set at the deployment-
                level.
            options (Optional[Dict[str, Any]]): Module-specific options.
                See :ref:`Module Configurations<module-configurations>`
                for detailed usage.
            tags (Optional[Dict[str, str]]): Module tags used to select
                which modules to process using CLI arguments.
                (``--tag <tag>...``)
            child_modules (Optional[List[Union[str, Dict[str, Any]]]]):
                Child modules that can be executed in parallel

        References:
            - `AWS CDK`_
            - `CloudFormation`_
            - `Serverless Framework`_
            - `Stacker`_
            - `Troposphere`_
            - `Terraform`_
            - `Kubernetes`_
            - :ref:`Module Configurations<module-configurations>` -
              detailed module ``options``
            - :ref:`Repo Structure<repo-structure>` - examples of
              directory structure
            - :ref:`command-deploy`
            - :ref:`command-destroy`
            - :ref:`command-plan`

        """
        self.name = name
        self.path = path
        self.class_path = class_path
        self.environments = environments or {}
        self.env_vars = env_vars or {}
        self.options = options or {}
        self.tags = tags or {}
        self.child_modules = child_modules

    @classmethod
    def from_list(cls, modules):
        """Instantiate ModuleDefinition from a list."""
        results = []
        for mod in modules:
            if isinstance(mod, str):
                results.append(cls(mod, mod, {}))
                continue
            if mod.get('parallel'):
                name = 'parallel_parent'
                child_modules = ModuleDefinition.from_list(mod.pop('parallel'))
                path = '[' + ', '.join([x.path for x in child_modules]) + ']'
                if mod:
                    LOGGER.warning(
                        'Invalid keys found in parallel module config have been ignored: %s',
                        ', '.join(mod.keys())
                    )
            else:
                name = mod.pop('name', mod['path'])
                child_modules = None
                path = mod.pop('path')
            results.append(cls(name,
                               path,
                               class_path=mod.pop('class_path', None),
                               environments=mod.pop('environments', {}),
                               env_vars=mod.pop('env_vars', {}),
                               options=mod.pop('options', {}),
                               tags=mod.pop('tags', {}),
                               child_modules=child_modules))
            if mod:
                LOGGER.warning(
                    'Invalid keys found in module %s have been ignored: %s',
                    name, ', '.join(mod.keys())
                )
        return results


class DeploymentDefinition(ConfigComponent):  # pylint: disable=too-many-instance-attributes
    """A deployment defines modules and options that affect the modules.

    Deployments are processed during a ``deploy``/``destroy``/``plan``
    action. If the processing of one deployment fails, the action will
    end.

    During a ``deploy``/``destroy`` action, the user has the option to
    select which deployment will run unless the ``CI`` environment
    variable is set, the ``--tag <tag>...`` cli option was provided, or
    only one deployment is defined.

    Example:
      .. code-block:: yaml

        deployments:
          - modules:  # minimum requirements for a deployment
              # "./" can alternatively be used for the module name to indicate
              # the current directory
              - my-module.cfn
            regions:
              - us-east-1
          - name: detailed-deployment  # optional
            modules:
              - path: my-other-modules.cfn
            regions:
              - us-east-1
            account_id:  # optional
              dev: 0000
              prod: 1111
            assume_role:  # optional
              dev: arn:aws:iam::0000:role/role-name
              prod: arn:aws:iam::1111:role/role-name
            environments:  # optional
              dev:
                region: us-east-1
                image_id: ami-abc123
            env_vars:  # optional environment variable overrides
              dev:
                AWS_PROFILE: foo
                APP_PATH:  # a list will be treated as components of a path on disk
                  - myapp.tf
                  - foo
              prod:
                AWS_PROFILE: bar
                APP_PATH:
                  - myapp.tf
                  - foo
              "*":  # applied to all environments
                ANOTHER_VAR: foo

    """

    def __init__(self, deployment):
        # type: (Dict[str, Any]) -> None
        """.. Runway deployment definition.

        Keyword Args:
            account_alias (Optional[Dict[str, str]]): A mapping of
                ``$environment: $alias`` that, if provided, is used to
                verify the currently assumed role or credentials.
            account_id (Optional[Dict[str, Union[str, int]]]): A mapping
                of ``$environment: $id`` that, if provided, is used to
                verify the currently assumed role or credentials.
            assume_role (Optional[Dict[str, Union[str, Dict[str, str]]]]):
                A mapping of ``$environment: $role`` or
                ``$environment: {arn: $role, duration: $int}`` to assume
                a role when processing a deployment. ``arn: $role`` can
                be used to apply the same role to all environment.
                ``post_deploy_env_revert: true`` can also be provided to
                revert credentials after processing.
            environments (Optional[Dict[str, Dict[str, Any]]]): Mapping for
                variables to environment names. When run, the variables
                defined here are merged with those in the
                ``.env``/``.tfenv``/environment config file and
                environments section of each module.
            env_vars (Optional[Dict[str, Dict[str, Any]]]): A mapping of
                OS environment variable overrides to apply when processing
                modules in the deployment. Can be defined per environment
                or for all environments using ``"*"`` as the environment
                name.
            modules (Optional[List[Dict[str, Any]]]): A list of modules
                to be processed in the order they are defined.
            module_options (Optional[Dict[str, Any]]): Options that are
                shared among all modules in the deployment.
            name (str): Name of the deployment. Used to more easily
                identify where different deployments begin/end in the logs.
            regions (List[str]): AWS region names where modules will be
                deployed/destroyed. Can optionally define as a map with
                ``parallel`` as the key and a list of regions as the value.
                See **parallel_regions** for more info.
            parallel_regions: Can be defined in place of ``regions.parallel[]``.
                This will cause all modules in the deployment to be executed
                in all provided regions in parallel (at the same time).
                Only takes effect when the ``CI`` environment variable is set,
                enabling non-interactive mode, as prompts will not be able
                to be presented. If ``CI`` is not set, the regions will be
                processed one at a time. This can be used in tandom with
                **parallel modules**. ``assume_role.post_deploy_env_revert``
                will always be ``true`` when run in parallel.

        References:
            - :class:`module<runway.config.ModuleDefinition>`
            - :ref:`command-deploy`
            - :ref:`command-destroy`
            - :ref:`command-plan`

        """
        self.account_alias = deployment.pop(
            'account_alias', deployment.pop('account-alias', {})
        )  # type: Optional[Dict[str, str]]
        self.account_id = deployment.pop(
            'account_id', deployment.pop('account-id', {})
        )  # type: Optional[Dict[str, Union[str, int]]]
        self.assume_role = deployment.pop(
            'assume_role', deployment.pop('assume-role', {})
        )  # type: Optional[Dict[str, Union[str, Dict[str, str]]]]
        self.environments = deployment.pop(
            'environments', {}
        )  # type: Optional[Dict[str, Dict[str, Any]]]
        self.env_vars = deployment.pop(
            'env_vars', deployment.pop('env-vars', {})
        )  # type: Optional[Dict[str, Dict[str, Any]]]
        if deployment.pop('current_dir', False):
            # Deprecated in 1.0 (late 2019). Retain for at least a major version.
            LOGGER.warning('DEPRECATION WARNING: The "current_dir" option has '
                           'been deprecated in favor of a "./" module '
                           'definition. Please update your config.')
            modules = ['.' + os.sep]
        else:
            if not deployment.get('modules'):
                LOGGER.error('No modules have been defined in your Runway '
                             'deployment.')
                sys.exit(1)
            modules = deployment.pop('modules')
        self.modules = ModuleDefinition.from_list(
            modules
        )  # type: List[ModuleDefinition]
        self.module_options = deployment.pop(
            'module_options', deployment.pop('module-options', {})
        )  # type: Optional(Dict[str, Any])
        self.name = deployment.pop('name')  # type: str
        self.regions = deployment.pop(
            'regions', []
        )  # type: Union[List[str], Dict[str, List[str]]]

        if self.regions and deployment.get('parallel_regions'):
            LOGGER.error('Found "regions" and "parallel_regions" in '
                         'deployment "%s"; only one can be defined',
                         self.name)
            sys.exit(1)
        if isinstance(self.regions, dict) and self.regions.get('parallel'):
            self.parallel_regions = self.regions.pop('parallel')
            self.regions = []
        else:
            self.parallel_regions = deployment.pop('parallel_regions', [])

        if deployment:
            LOGGER.warning(
                'Invalid keys found in deployment %s have been ignored: %s',
                self.name, ', '.join(deployment.keys())
            )

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
    """Tests can be defined as part of the Runway config file.

    This is to remove the need for complex Makefiles or scripts to initiate
    test runners. Simply define all tests for a project in the Runway
    config file and use the ``runway test`` :ref:`command<command-test>`
    to execute them.

    Example:
      .. code-block:: yaml

        tests:
          - name: my-test
            type: script
            required: false
            args:
              commands:
                - echo "Hello World!"

    """

    def __init__(self,
                 name,  # type: str
                 test_type,  # type: str
                 args=None,  # type: Optional[Dict[str, Any]]
                 required=True  # type: bool
                 # pylint only complains for python2
                 ):  # pylint: disable=bad-continuation
        # type: (...) -> None
        """.. Runway test definitions.

        Keyword Args:
            name (str): Name of the test. Used to more easily identify
                where different tests begin/end in the logs.
            type (str): The type of test to run. See
                :ref:`Build-in Test Types<built-in-test-types>`
                for supported test types.
            args (Optional[Dict[str, Any]]): Arguments to be passed to
                the test. Supported arguments vary by test type. See
                :ref:`Build-in Test Types<built-in-test-types>` for the
                list of arguments supported by each test type.
            required (bool):  If false, testing will continue if the test
                fails. *(default: true)*

        References:
            - :ref:`Build-in Test Types<built-in-test-types>` - Supported
              test types and their
              arguments
            - :ref:`test command<command-test>`

        """
        self.name = name
        self.type = test_type
        self.args = args or {}
        self.required = required

    @classmethod
    def from_list(cls, tests):
        # type: (List[Dict[str, Any]]) -> List[TestDefinition]
        """Instantiate TestDefinitions from a list."""
        results = []

        for index, test in enumerate(tests):
            name = test.pop('name', 'test_{}'.format(index + 1))
            results.append(cls(name, test.pop('type'),
                               test.pop('args', {}),
                               test.pop('required', False)))

            if test:
                LOGGER.warning(
                    'Invalid keys found in test %s have been ignored: %s',
                    name, ', '.join(test.keys())
                )
        return results


class Config(ConfigComponent):
    """The Runway config file is where all options are defined.

    It contains definitions for deployments, tests, and some global
    options that impact core functionality.

    The Runway config file can have two possible names, ``runway.yml``
    or ``runway.yaml``. It must be stored at the root of the directory
    containing all modules to be deployed.

    Example:
        .. code-block:: yaml

            ---
            # See full syntax at https://github.com/onicagroup/runway
            ignore_git_branch: true
            tests:
              - name: example
                type: script
                args:
                  commands:
                    - echo "Hello world"
            deployments:
              - modules:
                  - path: my-modules.cfn
                regions:
                  - us-east-1

    """

    accepted_names = ['runway.yml', 'runway.yaml']

    def __init__(self,
                 deployments,  # type: List[Dict[str, Any]]
                 tests=None,  # type: List[Dict[str, Any]]
                 ignore_git_branch=False  # type: bool
                 # pylint only complains for python2
                 ):  # pylint: disable=bad-continuation
        # type: (...) -> None
        """.. Top-level Runway config file.

        Keyword Args:
            deployments (List[Dict[str, Any]]): A list of
                :class:`deployments<runway.config.DeploymentDefinition>`
                that are processed in the order they are defined.
            tests (Optional[List[Dict[str, Any]]]): A list of
                :class:`tests<runway.config.TestDefinition>` that are
                processed in the order they are defined.
            ignore_git_branch (bool): Disable git branch lookup when
                using environment folders, non-git VCS, or defining the
                ``DEPLOY_ENVIRONMENT`` environment variable before
                execution. Note that defining ``DEPLOY_ENVIRONMENT``
                will automatically ignore the git branch.

        References:
            - :class:`deployment<runway.config.DeploymentDefinition>`
            - :class:`test<runway.config.TestDefinition>`

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
            result = Config(config_file.pop('deployments'),
                            config_file.pop('tests', []),
                            config_file.pop('ignore_git_branch',
                                            config_file.pop(
                                                'ignore-git-branch',
                                                False)))

            if config_file:
                LOGGER.warning(
                    'Invalid keys found in runway file have been ignored: %s',
                    ', '.join(config_file.keys())
                )
            return result

    @classmethod
    def find_config_file(cls, config_dir=None):
        # type: (Optional[str]) -> str
        """Find the Runway config file."""
        if not config_dir:
            config_dir = os.getcwd()

        for name in cls.accepted_names:
            conf_path = os.path.join(config_dir, name)
            if os.path.isfile(conf_path):
                return conf_path

        LOGGER.error('Runway config file was not found. Looking for one '
                     'of %s in %s', str(cls.accepted_names), config_dir)
        sys.exit(1)
