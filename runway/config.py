"""Runway config file module."""
# pylint: disable=super-init-not-called,too-many-lines
from typing import (Any, Dict, List, Optional,  # pylint: disable=unused-import
                    Union, Iterator, TYPE_CHECKING)

# python2 supported pylint is unable to load this when in a venv
from distutils.util import strtobool  # pylint: disable=no-name-in-module,import-error
import logging
import os
import sys

from six import string_types
import yaml

from .util import MutableMap
from .variables import Variable

# python2 supported pylint sees this is cyclic even though its only for type checking
# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from .context import Context  # noqa: F401 pylint: disable=unused-import

LOGGER = logging.getLogger('runway')
NoneType = type(None)


class ConfigComponent(MutableMap):
    """Base class for Runway config components.

    Attributes:
        SUPPORTS_VARIABLES: A list of directives that support the use of
            variable.
        PRE_PROCESS_VARIABLES: A list of directives that support the use of
            variables and needs to be resolved before the component is
            processed.

    """

    SUPPORTS_VARIABLES = ['env_vars', 'environments', 'parameters']  # type: List[str]
    PRE_PROCESS_VARIABLES = []  # type: List[str]

    @property
    def data(self):
        # type: () -> Dict[str, Any]
        """Sanitized output of __dict__ with properties added.

        Removes anything that starts with ``_``.

        """
        data = {}

        for key, val in self.__dict__.items():
            if not key.startswith('_'):
                data[key] = val

        for attr in self.SUPPORTS_VARIABLES:
            data[attr] = getattr(self, attr, None)

        return data

    @property
    def env_vars(self):
        # type: () -> Any
        """Access the value of an attribute that supports variables."""
        value = self._env_vars.value  # pylint: disable=no-member
        if isinstance(value, dict):
            return value
        raise ValueError('{}.env_vars is of type {}; expected type '
                         'of dict'.format(self.name, type(value)))

    @property
    def environments(self):
        # type: () -> Dict[Any, Any]
        """Access the value of an attribute that supports variables."""
        value = self._environments.value  # pylint: disable=no-member
        if isinstance(value, dict):
            return value
        raise ValueError('{}.environments is of type {}; expected type '
                         'of dict'.format(self.name, type(value)))

    @property
    def parameters(self):
        # type: () -> Dict[str, Any]
        """Access the value of an attribute that supports variables."""
        value = self._parameters.value  # pylint: disable=no-member
        if isinstance(value, dict):
            return value
        raise ValueError('{}.parameters is of type {}; expected type '
                         'of dict'.format(self.name, type(value)))

    def get(self, key, default=None):
        # type: (str, Any) -> Any
        """Implement evaluation of get."""
        return getattr(self, key, getattr(self, key.replace('-', '_'), default))

    def resolve(self, context, variables=None, pre_process=False):
        # type: ('Context', Optional[VariablesDefinition], bool) -> None
        """Resolve attributes that support variables.

        Args:
            context: The current context object.
            variables: Object containing variables passed to Runway.
            pre_process: Only resolve the variables that are required before
                the component is processed. If this is ``False``, all variables
                will be resolved. This is useful to prevent errors when
                variables cannot be resolved because the values are not
                populated until processing has begun.

        """
        for attr in (self.PRE_PROCESS_VARIABLES if pre_process
                     else self.SUPPORTS_VARIABLES):
            LOGGER.debug('Resolving %s.%s', self.name, attr)
            getattr(self, '_' + attr).resolve(context, variables=variables)

    def __getitem__(self, key):
        # type: (str) -> Any
        """Implement evaluation of self[key]."""
        result = getattr(self, key, getattr(self, key.replace('-', '_')))

        if isinstance(result, Variable):
            return result.value
        return result

    def __len__(self):
        # type: () -> int
        """Implement the built-in function len()."""
        return len(self.data)

    def __iter__(self):
        # type: () -> Iterator[Any]
        """Return iterator object that can iterate over all attributes."""
        return iter(self.data)


class ModuleDefinition(ConfigComponent):  # pylint: disable=too-many-instance-attributes
    """A module defines the directory to be processed and applicable options.

    It can consist of `CloudFormation`_ (using `CFNgin`_),
    `Terraform`_, `Serverless Framework`_, `AWS CDK`_, `Kubernetes`_, or
    a :ref:`Static Site<mod-staticsite>`. It is recommended to place the
    appropriate extension on each directory for identification (but it
    is not required). See :ref:`Repo Structure<repo-structure>` for
    examples of a module directory structure.

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
    | ``.web``         | :ref:`Static Site<mod-staticsite>`            |
    +------------------+-----------------------------------------------+

    A module is only deployed if there is a corresponding environment file
    present or parameters are provided. This can take the form of either a file
    in the module folder or the ``parameters`` option being defined. The naming
    format varies per-module type.
    See :ref:`Module Configurations<module-configurations>` for acceptable
    environment file name formats.

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
    per-module ``options``, parameters, environment variables,tags,
    and even a custom class for processing the module. The options that
    can be used with each module vary. For detailed information about
    module-specific options, see
    :ref:`Module Configurations<module-configurations>`.

    Example:
      .. code-block:: yaml

        deployments:
          - modules:
              - name: my-module
                path: my-module.tf
                environments:
                  prod: 111111111111/us-east-1
                  dev:
                    - 222222222222/us-east-1
                    - 333333333333/us-east-1
                  lab: true
                parameters:
                  image_id: ${var image_id.${env DEPLOY_ENVIRONMENT}}
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
      In this example, ``backend.tf`` will be deployed followed by the services
      that will be utilizing it. The services will be deployed in parallel.
      After the services have completed, ``frontend.tf`` will be deployed.

      .. code-block:: yaml

        deployments:
          - modules:
            - backend.tf
            - parallel:
              - servicea.cfn  # any normal module option can be used here
              - path: serviceb.cfn
              - path: servicec.cfn
                parameters:
                  count: ${var count.${env DEPLOY_ENVIRONMENT}}
            - frontend.tf

    """

    SUPPORTS_VARIABLES = ['class_path', 'env_vars', 'environments',
                          'options', 'parameters', 'path']

    def __init__(self,  # pylint: disable=too-many-arguments
                 name,  # type: str
                 path,  # type: str
                 class_path=None,  # type: Optional[str]
                 type_str=None,  # type: Optional[str]
                 environments=None,  # type: Optional[Dict[str, Dict[str, Any]]]
                 parameters=None,  # type: Optional[Dict[str, Any]]
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
                file. This cannot be higher than the Runway config file. See
                `Path`_ for detailed usage.
            class_path (Optional[str]): Path to custom Runway module class.
                Also used for static site deployments. See
                :ref:`Module Configurations<module-configurations>` for
                detailed usage.
            type_str (Optional[str]): Alias for type of module to use
                :ref:`Module Configurations<module-configurations>` for
                detailed usage.
            environments (Optional[Dict[str, Dict[str, Any]]]): Optional
                mapping of environment names to a booleon value used to
                explicitly deploy or not deploy in an environment. This
                can be used when an environment specific variables file
                and parameters are not needed to force a module to deploy
                anyway or, explicitly skip a module even if a file or
                parameters are found. The mapping can also have a string
                (or list of strings) value of $ACCOUNT_ID/$REGION to lock
                an environment to specific regions in a specific accounts.
                If it matches, it will act as an explicit deploy.
            env_vars (Optional[Dict[str, Dict[str, Any]]]): A mapping of
                OS environment variable overrides to apply when processing
                modules in the deployment. Can be defined per environment
                or for all environments by omiting the environment name.
                Takes precedence over values set at the deployment-level.
            options (Optional[Dict[str, Any]]): Module-specific options.
                See :ref:`Module Configurations<module-configurations>`
                for detailed usage. Takes precedence over values set at the
                deployment-level.
            parameters (Optional(Dict[str, Any])): Module level parameters that
                are akin to a `CloudFormation`_ parameter in functionality.
                These can be used to pass variable values to your modules in
                place of a ``.env``/``.tfenv``/environment config file.
                Through the use of `Lookups`_, the value can differ per
                deploy environment, region, etc.
            tags (Optional[Dict[str, str]]): Module tags used to select
                which modules to process using CLI arguments.
                (``--tag <tag>...``)
            child_modules (Optional[List[Union[str, Dict[str, Any]]]]):
                Child modules that can be executed in parallel

        .. rubric:: Lookup Resolution

        +---------------------+-----------------------------------------------+
        | Keyword / Directive | Support                                       |
        +=====================+===============================================+
        |  ``name``           | None                                          |
        +---------------------+-----------------------------------------------+
        |  ``path``           | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+
        |  ``class_path``     | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+
        |  ``environments``   | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+
        |  ``env_vars``       | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+
        |  ``options``        | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+
        |  ``parameters``     | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+
        |  ``tags``           | None                                          |
        +---------------------+-----------------------------------------------+

        References:
            - `AWS CDK`_
            - `CloudFormation`_
            - `Serverless Framework`_
            - `CFNgin`_
            - `Troposphere`_
            - `Terraform`_
            - `Kubernetes`_
            - :ref:`Static Site<mod-staticsite>`
            - :ref:`Module Configurations<module-configurations>` -
              detailed module ``options``
            - :ref:`Repo Structure<repo-structure>` - examples of
              directory structure
            - :ref:`command-deploy`
            - :ref:`command-destroy`
            - :ref:`command-plan`

        """
        self.name = name
        self._path = Variable(name + '.path', path, 'runway')
        self._class_path = Variable(name + '.class_path', class_path, 'runway')
        self.type = type_str
        self._environments = Variable(name + '.environments',
                                      environments or {}, 'runway')
        self._parameters = Variable(name + '.parameters', parameters or {},
                                    'runway')
        self._env_vars = Variable(name + '.env_vars', env_vars or {}, 'runway')
        self._options = Variable(name + '.options', options or {}, 'runway')
        self.tags = tags or {}
        self.child_modules = child_modules or []

    @property
    def class_path(self):
        # type: () -> Optional[str]
        """Access the value of an attribute that supports variables."""
        value = self._class_path.value
        if not value:
            return None
        if isinstance(value, str):
            return value
        raise ValueError('{}.class_path = {} is of type {}; expected type '
                         'of str'.format(self.name, value, type(value)))

    @property
    def options(self):
        # type: () -> Dict[Any, Any]
        """Access the value of an attribute that supports variables."""
        value = self._options.value
        if isinstance(value, dict):
            return value
        raise ValueError('{}.options is of type {}; expected type '
                         'of dict'.format(self.name, type(value)))

    @property
    def path(self):
        # type: () -> str
        """Access the value of an attribute that supports variables."""
        value = self._path.value  # pylint: disable=no-member
        if isinstance(value, str):
            return value
        raise ValueError('{}.path is of type {}; expected type '
                         'of str'.format(self.name, type(value)))

    @classmethod
    def from_list(cls, modules):
        # type: (List[Union[Dict[str, Any], str]]) -> List[ModuleDefinition]
        """Instantiate ModuleDefinition from a list."""
        results = []

        for mod in modules:
            if isinstance(mod, str):
                results.append(cls(name=mod, path=mod))
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
                               type_str=mod.pop('type', None),
                               environments=mod.pop('environments', {}),
                               env_vars=mod.pop('env_vars', {}),
                               options=mod.pop('options', {}),
                               parameters=mod.pop('parameters', {}),
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
                type: cloudformation
            regions:
              - us-east-1
            environments:
              prod: 111111111111/us-east-1
              dev:
                - 222222222222/us-east-1
                - 333333333333/us-east-1
              lab: true
            account_id: ${var account_ids}  # optional
            assume_role: ${var assume_role}  # optional
            parameters:  # optional
                region: ${env AWS_REGION}
                image_id: ${var image_id.${env DEPLOY_ENVIRONMENT}}
            env_vars:  # optional environment variable overrides
                AWS_PROFILE: ${var aws_profile.${env DEPLOY_ENVIRONMENT}::default=default}
                APP_PATH: ${var app_path.${env DEPLOY_ENVIRONMENT}}

    """

    SUPPORTS_VARIABLES = ['account_alias', 'account_id', 'assume_role',
                          'env_vars', 'environments', 'module_options',
                          'regions', 'parallel_regions', 'parameters']
    PRE_PROCESS_VARIABLES = ['account_alias', 'account_id', 'assume_role',
                             'env_vars', 'regions']

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
            environments (Optional[Dict[str, Dict[str, Any]]]): Optional
                mapping of environment names to a booleon value used to
                explicitly enable or disable in an environment. This
                can be used when an environment specific variables file
                and parameters are not needed to force a module to enable
                anyway or, explicitly skip a module even if a file or
                parameters are found. The mapping can also have a string
                (or list of strings) value of $ACCOUNT_ID/$REGION to lock
                an environment to specific regions in a specific accounts.
                If it matches, it will act as an explicit enable.
            env_vars (Optional[Dict[str, Dict[str, Any]]]): A mapping of
                OS environment variable overrides to apply when processing
                modules in the deployment. Can be defined per environment
                or for all environments by omiting the environment name.
            modules (Optional[List[Dict[str, Any]]]): A list of modules
                to be processed in the order they are defined.
            module_options (Optional[Dict[str, Any]]): Options that are
                shared among all modules in the deployment.
            name (str): Name of the deployment. Used to more easily
                identify where different deployments begin/end in the logs.
            type (str): The type of module we are deploying. By default
                Runway will first check to see if you explicitly specify
                the module type, after that it will check to see if a
                valid module extension exists on the directory, and
                finally it will attempt to autodetect the type of module.
                Valid values are: ``serverless``, ``terraform``, ``cdk``,
                ``kubernetes``, ``cloudformation``, ``static``.
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
            parameters (Optional(Dict[str, Any])): Module level parameters that
                are akin to a `CloudFormation`_ parameter in functionality.
                These can be used to pass variable values to your modules in
                place of a ``.env``/``.tfenv``/environment config file.
                Through the use of `Lookups`_, the value can differ per
                deploy environment, region, etc.

        .. rubric:: Lookup Resolution

        .. important:: Due to how a deployment is processed, values are
                       resolved twice. Once before processing and once during
                       processing. Because of this, the keywords/directives
                       that are resolved before processing will not have
                       access to values set during process like ``AWS_REGION``,
                       ``AWS_DEFAULT_REGION``, and ``DEPLOY_ENVIRONMENT`` for
                       the pre-processing resolution but, if they are resolved
                       again during processing, these will be available. To
                       avoide errors during the first resolution due to the
                       value not existing, provide a default value for the
                       :ref:`Lookup <Lookups>`.

        +---------------------+-----------------------------------------------+
        | Keyword / Directive | Support                                       |
        +=====================+===============================================+
        | ``account_alias``   | `env lookup`_ (``AWS_REGION`` and             |
        |                     | ``AWS_DEFAULT_REGION`` will not have been set |
        |                     | by Runway yet), `var lookup`_                 |
        +---------------------+-----------------------------------------------+
        | ``account_id``      | `env lookup`_ (``AWS_REGION`` and             |
        |                     | ``AWS_DEFAULT_REGION`` will not have been set |
        |                     | by Runway yet), `var lookup`_                 |
        +---------------------+-----------------------------------------------+
        |  ``assume_role``    | `env lookup`_ (``AWS_REGION`` and             |
        |                     | ``AWS_DEFAULT_REGION`` will not have been set |
        |                     | by Runway yet), `var lookup`_                 |
        +---------------------+-----------------------------------------------+
        |  ``environments``   | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+
        |  ``env_vars``       | `env lookup`_ (``AWS_REGION``,                |
        |                     | ``DEPLOY_ENVIRONMENT``, and                   |
        |                     | ``AWS_DEFAULT_REGION`` will not have been set |
        |                     | by Runway during pre-process resolution.      |
        |                     | provide a default value to avoide errors.),   |
        |                     | `var lookup`_                                 |
        +---------------------+-----------------------------------------------+
        |  ``modules``        | No direct support. See `module`_ for details  |
        |                     | on support within a module definition.        |
        +---------------------+-----------------------------------------------+
        |  ``module_options`` | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+
        |  ``name``           | None                                          |
        +---------------------+-----------------------------------------------+
        |  ``regions``        | `env lookup`_ (``AWS_REGION`` and             |
        |                     | ``AWS_DEFAULT_REGION`` will not have been set |
        |                     | by Runway yet), `var lookup`_                 |
        +---------------------+-----------------------------------------------+
        | ``parallel_regions``| `env lookup`_ (``AWS_REGION`` and             |
        |                     | ``AWS_DEFAULT_REGION`` will not have been set |
        |                     | by Runway yet), `var lookup`_                 |
        +---------------------+-----------------------------------------------+
        |  ``parameters``     | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+

        References:
            - :class:`module<runway.config.ModuleDefinition>`
            - :ref:`command-deploy`
            - :ref:`command-destroy`
            - :ref:`command-plan`

        """
        self._reverse = False
        self.name = deployment.pop('name')  # type: str
        self._account_alias = Variable(
            self.name + '.account_alias', deployment.pop(
                'account_alias', deployment.pop('account-alias', {})
            ), 'runway'
        )  # type: Variable
        self._account_id = Variable(self.name + '.account_id', deployment.pop(
            'account_id', deployment.pop('account-id', {})
        ), 'runway')  # type: Variable
        self._assume_role = Variable(
            self.name + '.assume_role', deployment.pop(
                'assume_role', deployment.pop('assume-role', {})
            ), 'runway'
        )  # type: Variable
        self._environments = Variable(
            self.name + '.environments', deployment.pop('environments', {}),
            'runway'
        )  # type: Variable
        self._parameters = Variable(
            self.name + '.parameters', deployment.pop('parameters', {}),
            'runway'
        )  # type: Variable
        self._env_vars = Variable(self.name + '.env_vars', deployment.pop(
            'env_vars', deployment.pop('env-vars', {})
        ), 'runway')  # type: Variable
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
        self._module_options = Variable(
            self.name + '.module_options', deployment.pop(
                'module_options', deployment.pop('module-options', {})
            ), 'runway'
        )  # type: Variable

        # should add variable resolve here to support parallel region
        # dict in the resolved variable
        regions = deployment.pop(
            'regions', []
        )

        if regions and deployment.get('parallel_regions'):
            LOGGER.error('Found "regions" and "parallel_regions" in '
                         'deployment "%s"; only one can be defined',
                         self.name)
            sys.exit(1)
        if isinstance(regions, dict) and regions.get('parallel'):
            self._parallel_regions = Variable(
                self.name + '.parallel_regions', regions.pop('parallel'),
                'runway'
            )  # type: Variable
            self._regions = Variable(self.name + '.regions',
                                     [], 'runway')  # type: Variable
        else:
            self._regions = Variable(self.name + '.regions',
                                     regions, 'runway')
            self._parallel_regions = Variable(
                self.name + '.parallel_regions',
                deployment.pop('parallel_regions', []),
                'runway'
            )

        if deployment:
            LOGGER.warning(
                'Invalid keys found in deployment %s have been ignored: %s',
                self.name, ', '.join(deployment.keys())
            )

    @property
    def account_alias(self):
        # type: () -> Union[Dict[Any, Any], str]
        """Access the value of an attribute that supports variables."""
        value = self._account_alias.value
        if isinstance(value, (dict, string_types)):
            return value
        raise ValueError('{}.account_alias is of type {}; expected type '
                         'of dict or str'.format(self.name, type(value)))

    @property
    def account_id(self):
        # type: () -> Union[Dict[Any, Any], str]
        """Access the value of an attribute that supports variables."""
        value = self._account_id.value
        if isinstance(value, (dict, string_types)):
            return value
        if isinstance(value, int):
            return str(value)
        raise ValueError('{}.account_id is of type {}; expected type '
                         'of dict, int, or str'.format(self.name, type(value)))

    @property
    def assume_role(self):
        # type: () -> Union[Dict[Any, Any], str]
        """Access the value of an attribute that supports variables."""
        value = self._assume_role.value
        if isinstance(value, (dict, string_types)):
            return value
        raise ValueError('{}.assume_role is of type {}; expected type '
                         'of dict or str'.format(self.name, type(value)))

    @property
    def module_options(self):
        # type: () -> Dict[Any, Any]
        """Access the value of an attribute that supports variables."""
        value = self._module_options.value
        if isinstance(value, dict):
            return value
        raise ValueError('{}.module_options is of type {}; expected type '
                         'of dict'.format(self.name, type(value)))

    @property
    def regions(self):
        # type: () -> List[str]
        """Access the value of an attribute that supports variables."""
        value = self._regions.value
        if isinstance(value, list):
            if self._reverse:
                return value[::-1]
            return value
        raise ValueError('{}.regions is of type {}; expected type '
                         'of list'.format(self.name, type(value)))

    @property
    def parallel_regions(self):
        # type: () -> List[str]
        """Access the value of an attribute that supports variables."""
        value = self._parallel_regions.value
        if isinstance(value, list):
            return value
        raise ValueError('{}.parallel_regions is of type {}; expected type '
                         'of list'.format(self.name, type(value)))

    def reverse(self):
        """Reverse the order of modules and regions."""
        if self._reverse:
            self._reverse = False
        else:
            self._reverse = True
        self.modules.reverse()

    @classmethod
    def from_list(cls, deployments):
        # type: (Optional[List[Dict[str, Any]]]) -> List[DeploymentDefinition]
        """Instantiate DeploymentDefinitions from a list."""
        results = []

        if not deployments:
            return []

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

    SUPPORTS_VARIABLES = ['args', 'required']

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

        .. rubric:: Lookup Resolution

        .. note:: Runway does not set ``AWS_REGION`` or ``AWS_DEFAULT_REGION``
                  environment variables. If the ``DEPLOY_ENVIRONMENT``
                  environment variable is not manually set, it will always
                  be ``test`` and is not determined from the branch or
                  directory.

        +---------------------+-----------------------------------------------+
        | Keyword / Directive | Support                                       |
        +=====================+===============================================+
        | ``args``            | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+
        | ``required``        | `env lookup`_, `var lookup`_                  |
        +---------------------+-----------------------------------------------+

        References:
            - :ref:`Build-in Test Types<built-in-test-types>` - Supported
              test types and their
              arguments
            - :ref:`test command<command-test>`

        """
        self.name = name
        self.type = test_type
        self._args = Variable(self.name + '.args', args or {}, 'runway')
        self._required = Variable(self.name + '.required', required, 'runway')

    @property
    def args(self):
        # type: () -> Dict[str, Any]
        """Access the value of an attribute that supports variables."""
        value = self._args.value
        if isinstance(value, dict):
            return value
        raise ValueError('{}.args is of type {}; expected type '
                         'of dict'.format(self.name, type(value)))

    @property
    def required(self):
        # type: () -> bool
        """Access the value of an attribute that supports variables."""
        value = self._required.value
        if isinstance(value, bool):
            return value
        try:
            value = strtobool(value)
            return value
        except ValueError:
            pass
        raise ValueError('{}.required is of type {}; expected type '
                         'of bool'.format(self.name, type(value)))

    @classmethod
    def from_list(cls, tests):
        # type: (Optional[List[Dict[str, Any]]]) -> List[TestDefinition]
        """Instantiate TestDefinitions from a list."""
        results = []

        if not tests:
            return []

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


class VariablesDefinition(MutableMap):
    """A variable definitions for the Runway config file.

    Runway variables are used to fill values that could change based on any
    number of circumstances. They can also be used to simplify the Runway config
    file by pulling lengthy definitions into another file. Variables can be used
    in the config file by providing the `var lookup`_ to any keyword/directive
    that supports :ref:`Lookups <Lookups>`.

    By default, Runway will look for and load a ``runway.variables.yml`` or
    ``runway.variables.yaml`` file that is in the same directory as the
    Runway config file. The file path and name of the file can optionally be
    defined in the config file. If the file path is explicitly provided and
    the file can't be found, an error will be raised.

    Variables can also be defined in the Runway config file directly. This can
    either be in place of a dedicated variables file, extend an existing file,
    or override values from the file.

    .. rubric:: Lookup Resolution

    Runway lookup resolution is not supported within the variables definition
    block or variables file. Attempts to use Runway :ref:`Lookups <Lookups>`
    within the variables definition block or variables file will result in
    the literal value being processed.

    Example:
      .. code-block:: yaml

        variables:
          sys_path: ./  # defaults to the current directory
          file_path: secrets.yaml
          # define additional variables or override those in the variables file
          another_var: some_value
        deployments:
          - modules:
              - ${var sampleapp.definition}
            regions: ${var sampleapp.regions}

    """

    default_names = ['runway.variables.yml', 'runway.variables.yaml']

    def __init__(self, file_path=None, sys_path=None, **kwargs):
        """.. Not really needed but cleans up the docs.

        Keyword Args:
            file_path: Explicit path to a variables file. If it cannot be found
                Runway will exit.
            sys_path: Directory to base relative paths off of.

        """
        self._file_path = file_path
        self._sys_path = sys_path
        super(VariablesDefinition, self).__init__(**kwargs)

    @classmethod
    def find_file(cls, file_path=None, sys_path=None):
        # type: (Any, Any) -> Optional[str]
        """Find a Runway variables file.

        Args:
            file_path: Explicit path to a variables file. If it cannot be found
                Runway will exit.
            sys_path: Directory to base relative paths off of.

        Returns:
            Verified path to a file.

        Raises:
            TypeError: file_path or sys_path is not a string.

        """
        if not (isinstance(file_path, (str, NoneType)) and
                isinstance(file_path, (str, NoneType))):
            raise TypeError('file_path and sys_path of VariablesDefinition '
                            'must of be of type str but got types {} and {}'.format(
                                type(file_path), type(sys_path)))
        if not sys_path:
            sys_path = os.getcwd()

        if file_path:
            result = os.path.join(sys_path, file_path)
            if os.path.isfile(result):
                return result
            LOGGER.error('The provided variables "%s" file could not '
                         'be found.', result)
            sys.exit(1)

        for name in cls.default_names:
            result = os.path.join(sys_path, name)
            if os.path.isfile(result):
                return result

        LOGGER.info('Could not find %s in the current directory. '
                    'Continuing without a variables file.',
                    ' or '.join(cls.default_names))
        return None

    @classmethod
    def load(cls, **kwargs):
        # type: (Dict[str, Any]) -> VariablesDefinition
        """Load variables."""
        file_path = cls.find_file(file_path=kwargs.pop('file_path', None),
                                  sys_path=kwargs.pop('sys_path', None))

        if file_path:
            variables = cls._load_from_file(file_path)

            for key, val in kwargs.items():
                variables[key] = val

            return variables

        return cls(**kwargs)

    @classmethod
    def _load_from_file(cls, file_path):
        # type: (str) -> VariablesDefinition
        """Load the variables file into an object."""
        if not os.path.isfile(file_path):
            LOGGER.error('The provided variables "%s" file could not '
                         'be found.', file_path)
            sys.exit(1)

        with open(file_path) as data_file:
            return cls(**yaml.safe_load(data_file))


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
                 ignore_git_branch=False,  # type: bool
                 variables=None  # type: Optional[Dict[str, Any]]
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
            variables (Optional[Dict[str, Any]]): A map that defines the
                location of a variables file and/or the variables
                themselves.

        .. rubric:: Lookup Resolution

        +---------------------+-----------------------------------------------+
        | Keyword / Directive | Support                                       |
        +=====================+===============================================+
        | ``deployments``     | No direct support. See `Deployment`_ for      |
        |                     | details on support within a deploymet         |
        |                     | definition.                                   |
        +---------------------+-----------------------------------------------+
        | ``tests``           | No direct support. See `Test`_ for details on |
        |                     | support within a test definition.             |
        +---------------------+-----------------------------------------------+
        |``ignore_git_branch``| None                                          |
        +---------------------+-----------------------------------------------+
        | ``variables``       | None                                          |
        +---------------------+-----------------------------------------------+

        References:
            - :class:`deployment<runway.config.DeploymentDefinition>`
            - :class:`test<runway.config.TestDefinition>`

        """
        self.deployments = DeploymentDefinition.from_list(deployments)
        self.tests = TestDefinition.from_list(tests)
        self.ignore_git_branch = ignore_git_branch

        variables = variables or {}
        self.variables = VariablesDefinition.load(**variables)

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
                                                False)),
                            config_file.pop('variables', {}))

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
