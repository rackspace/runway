"""CFNgin config."""
import copy
import logging
import sys
import warnings
from io import StringIO
from string import Template

import yaml
from schematics import Model
from schematics.exceptions import BaseError as SchematicsError
from schematics.exceptions import UndefinedValueError, ValidationError
from schematics.types import (
    BaseType,
    BooleanType,
    DictType,
    ListType,
    ModelType,
    StringType,
)
from six import text_type

from runway.util import DOC_SITE

from .. import exceptions
from ..lookups import register_lookup_handler
from ..util import SourceProcessor, merge_map, yaml_to_ordered_dict
from .translators import *  # noqa pylint: disable=wildcard-import

LOGGER = logging.getLogger(__name__)


def render_parse_load(raw_config, environment=None, validate=True):
    """Encapsulate the render -> parse -> validate -> load process.

    Args:
        raw_config (str): The raw CFNgin configuration string.
        environment (Optional[Dict[str, Any]]): Any environment values that
            should be passed to the config.
        validate (bool): If provided, the config is validated before being
            loaded.

    Returns:
        :class:`Config`: The parsed CFNgin config.

    """
    pre_rendered = render(raw_config, environment)

    rendered = process_remote_sources(pre_rendered, environment)

    config = parse(rendered)

    # For backwards compatibility, if the config doesn't specify a namespace,
    # we fall back to fetching it from the environment, if provided.
    if config.namespace is None:
        namespace = environment.get("namespace")
        if namespace:
            LOGGER.warning(
                "specifying namespace in the environment is "
                "deprecated; to learn how to specify it correctly "
                "visit %s/page/cfngin/configuration.html#namespace",
                DOC_SITE,
            )
            config.namespace = namespace

    if validate:
        config.validate()

    return load(config)


def render(raw_config, environment=None):
    """Render a config, using it as a template with the environment.

    Args:
        raw_config (str): The raw CFNgin configuration string.
        environment (Optional[Dict[str, Any]]): Any environment values that
            should be passed to the config.

    Returns:
        str: The CFNgin configuration populated with any values passed from
            the environment.

    """
    template = Template(raw_config)
    buff = StringIO()
    if not environment:
        environment = {}
    try:
        substituted = template.substitute(**environment)
    except KeyError as err:
        raise exceptions.MissingEnvironment(err.args[0])
    except ValueError:
        # Support "invalid" placeholders for lookup placeholders.
        # needs to pass a Dict for correct error handling by the built-in
        substituted = template.safe_substitute(**environment)

    if not isinstance(substituted, text_type):
        substituted = substituted.decode("utf-8")

    buff.write(substituted)
    buff.seek(0)
    return buff.read()


def parse(raw_config):
    """Parse a raw yaml formatted CFNgin config.

    Args:
        raw_config (str): The raw CFNgin configuration string in yaml format.

    Returns:
        :class:`Config`: The parsed CFNgin config.

    """
    # Convert any applicable dictionaries back into lists
    # This is necessary due to the move from lists for these top level config
    # values to either lists or OrderedDicts.
    # Eventually we should probably just make them OrderedDicts only.
    config_dict = yaml_to_ordered_dict(raw_config)
    if config_dict:
        for top_level_key in [
            "stacks",
            "pre_build",
            "post_build",
            "pre_destroy",
            "post_destroy",
        ]:
            top_level_value = config_dict.get(top_level_key)
            if isinstance(top_level_value, dict):
                tmp_list = []
                for key, value in top_level_value.items():
                    tmp_dict = copy.deepcopy(value)
                    if top_level_key == "stacks":
                        tmp_dict["name"] = key
                    tmp_list.append(tmp_dict)
                config_dict[top_level_key] = tmp_list

    # Top-level excess keys are removed by Config._convert, so enabling strict
    # mode is fine here.
    try:
        return Config(config_dict, strict=True)
    except SchematicsError as err:
        raise exceptions.InvalidConfig(err.errors)


def load(config):
    """Load a CFNgin configuration by modifying syspath, loading lookups, etc.

    Args:
        config (:class:`Config`): The CFNgin config to load.

    Returns:
        :class:`Config`: The CFNgin config provided above.

    """
    if config.sys_path:
        LOGGER.debug("appending to sys.path: %s", config.sys_path)
        sys.path.append(config.sys_path)
        LOGGER.debug("sys.path: %s", sys.path)
    if config.lookups:
        for key, handler in config.lookups.items():
            register_lookup_handler(key, handler)

    return config


def dump(config):
    """Dump a CFNgin Config object as yaml.

    Args:
        config (:class:`Config`): The CFNgin Config object.

    Returns:
        str: The yaml formatted CFNgin Config.

    """
    return yaml.safe_dump(
        config.to_primitive(),
        default_flow_style=False,
        encoding="utf-8",
        allow_unicode=True,
    )


def process_remote_sources(raw_config, environment=None):
    """Stage remote package sources and merge in remote configs.

    Args:
        raw_config (str): The raw CFNgin configuration string.
        environment (Optional[Dict, Any]): Any environment values that should
            be passed to the config.

    Returns:
        str: The raw CFNgin configuration string.

    """
    config = yaml.safe_load(raw_config)
    if config and config.get("package_sources"):
        processor = SourceProcessor(
            sources=config["package_sources"],
            cfngin_cache_dir=config.get(
                "cfngin_cache_dir", config.get("stacker_cache_dir")
            ),
        )
        processor.get_package_sources()
        if processor.configs_to_merge:
            for i in processor.configs_to_merge:
                LOGGER.debug("merging in remote config: %s", i)
                remote_config = yaml.safe_load(open(i))
                config = merge_map(remote_config, config)
            # Call the render again as the package_sources may have merged in
            # additional environment lookups
            if not environment:
                environment = {}
            return render(str(config), environment)

    return raw_config


class AnyType(BaseType):
    """Any type."""


class LocalPackageSource(Model):
    """Local package source model.

    Package source located on a local disk.

    Attributes:
        configs (ListType): List of CFNgin config paths to execute.
        paths (ListType): List of paths to append to ``sys.path``.
        source (StringType): Source.

    """

    configs = ListType(StringType, serialize_when_none=False)
    paths = ListType(StringType, serialize_when_none=False)
    source = StringType(required=True)


class GitPackageSource(Model):
    """Git package source model.

    Package source located in a git repo.

    Attributes:
        branch (StringType): Branch name.
        commit (StringType): Commit hash.
        configs (ListType): List of CFNgin config paths to execute.
        paths (ListType): List of paths to append to ``sys.path``.
        tag (StringType): Git tag.
        uri (StringType): Remote git repo URI.

    """

    branch = StringType(serialize_when_none=False)
    commit = StringType(serialize_when_none=False)
    configs = ListType(StringType, serialize_when_none=False)
    paths = ListType(StringType, serialize_when_none=False)
    tag = StringType(serialize_when_none=False)
    uri = StringType(required=True)


class S3PackageSource(Model):
    """S3 package source model.

    Package source located in AWS S3.

    Attributes:
        bucket (StringType): AWS S3 bucket name.
        configs (ListType): List of CFNgin config paths to execute.
        key (StringType): Object key. The object should be a zip file.
        paths (ListType): List of paths to append to ``sys.path``.
        requester_pays (BooleanType): AWS S3 requester pays option.
        use_latest (BooleanType): Use the latest version of the object.

    """

    bucket = StringType(required=True)
    configs = ListType(StringType, serialize_when_none=False)
    key = StringType(required=True)
    paths = ListType(StringType, serialize_when_none=False)
    requester_pays = BooleanType(serialize_when_none=False)
    use_latest = BooleanType(serialize_when_none=False)


class PackageSources(Model):
    """Package sources model.

    Attributes:
        git (GitPackageSource): Package source located in a git repo.
        local (LocalPackageSource): Package source located on a local disk.
        s3 (S3PackageSource): Package source located in AWS S3.

    """

    git = ListType(ModelType(GitPackageSource))
    local = ListType(ModelType(LocalPackageSource))
    s3 = ListType(ModelType(S3PackageSource))


class Hook(Model):
    """Hook module.

    Attributes:
        args (DictType)
        data_key (StringType)
        enabled (BooleanType)
        path (StringType)
        required (BooleanType)

    """

    args = DictType(AnyType)
    data_key = StringType(serialize_when_none=False)
    enabled = BooleanType(default=True)
    path = StringType(required=True)
    required = BooleanType(default=True)


class Target(Model):
    """Target model.

    Attributes:
        name (StringType)
        required_by (ListType)
        requires (ListType)

    """

    name = StringType(required=True)
    required_by = ListType(StringType, serialize_when_none=False)
    requires = ListType(StringType, serialize_when_none=False)


class Stack(Model):
    """Stack model.

    Attributes:
        class_path (StringType)
        description (StringType)
        enabled (BooleanType)
        in_progress_behavior (StringType)
        locked (BooleanType)
        name (StringType)
        parameters (DictType)
        profile (StringType)
        protected (BooleanType)
        region (StringType)
        required_by (ListType)
        requires (ListType)
        stack_name (StringType)
        stack_policy_path (StringType)
        tags (DictType)
        template_path (StringType)
        termination_protection (BooleanType)
        variables (DictType)

    """

    class_path = StringType(serialize_when_none=False)
    description = StringType(serialize_when_none=False)
    enabled = BooleanType(default=True)
    in_progress_behavior = StringType(serialize_when_none=False)
    locked = BooleanType(default=False)
    name = StringType(required=True)
    parameters = DictType(AnyType, serialize_when_none=False)
    profile = StringType(serialize_when_none=False)
    protected = BooleanType(default=False)
    region = StringType(serialize_when_none=False)
    required_by = ListType(StringType, serialize_when_none=False)
    requires = ListType(StringType, serialize_when_none=False)
    stack_name = StringType(serialize_when_none=False)
    stack_policy_path = StringType(serialize_when_none=False)
    tags = DictType(StringType, serialize_when_none=False)
    template_path = StringType(serialize_when_none=False)
    termination_protection = BooleanType(default=False)
    variables = DictType(AnyType, serialize_when_none=False)

    def validate_class_path(self, data, value):
        """Validate class pass."""
        if value and data["template_path"]:
            raise ValidationError(
                "template_path cannot be present when class_path is provided."
            )
        self.validate_stack_source(data)

    def validate_template_path(self, data, value):
        """Validate template path."""
        if value and data["class_path"]:
            raise ValidationError(
                "class_path cannot be present when template_path is provided."
            )
        self.validate_stack_source(data)

    @staticmethod
    def validate_stack_source(data):
        """Validate stack source."""
        # Locked stacks don't actually need a template, since they're
        # read-only.
        if data["locked"]:
            return

        if not (data["class_path"] or data["template_path"]):
            raise ValidationError("class_path or template_path is required.")

    def validate_parameters(self, data, value):  # pylint: disable=no-self-use
        """Validate parameters."""
        if value:
            stack_name = data["name"]
            raise ValidationError(
                "DEPRECATION: Stack definition %s contains "
                "deprecated 'parameters', rather than 'variables'. You are"
                " required to update your config. See "
                "https://docs.onica.com/projects/runway/en/release/cfngin/"
                "config.html#variables for additional information." % stack_name
            )
        return value


class Config(Model):
    """Python representation of a CFNgin config file.

    This is used internally by CFNgin to parse and validate a yaml formatted
    CFNgin configuration file, but can also be used in scripts to generate a
    CFNgin config file before handing it off to CFNgin to build/destroy.

    Example::

        from runway.cfngin.config import dump, Config, Stack

        vpc = Stack({
            "name": "vpc",
            "class_path": "blueprints.VPC"})

        config = Config()
        config.namespace = "prod"
        config.stacks = [vpc]

        print dump(config)

    Attributes:
        cfngin_bucket (StringType): Bucket to use for CFNgin resources (e.g.
            CloudFormation templates). May be an empty string.
        cfngin_bucket_region (StringType): Explicit region to use for
            ``cfngin_bucket``.
        cfngin_cache_dir (StringType): Local directory to use for caching.
        log_formats (DictType): Custom formatting for log messages.
        lookups (DictType): Register custom lookups.
        mappings (DictType): Mappings that will be added to all stacks.
        namespace (StringType): Namespace to prepend to everything.
        namespace_delimiter (StringType): Character used to separate
            ``namespace`` and anything it prepends.
        package_sources (ModelType): Remote source locations.
        persistent_graph_key (str): S3 object key were the persistent graph
            is stored.
        post_build (ListType): Hooks to run after a build action.
        post_destroy (ListType): Hooks to run after a destroy action.
        pre_build (ListType): Hooks to run before a build action.
        pre_destroy (ListType): Hooks to run before a destroy action.
        service_role (StringType): IAM role for CloudFormation to use.
        stacker_bucket (StringType): [DEPRECATED] Replaced by
            ``cfngin_bucket``, support will be retained until the release
            of version 2.0.0 at the earliest.
        stacker_bucket_region (StringType): [DEPRECATED] Replaced by
            ``cfngin_bucket_region``, support will be retained until the
            release of version 2.0.0 at the earliest.
        stacker_cache_dir (StringType): [DEPRECATED] Replaced by
            ``cfngin_cache_dir``, support will be retained until the release
            of version 2.0.0 at the earliest.
        stacks (ListType): Stacks to be processed.
        sys_path (StringType): Relative or absolute path to use as the work
            directory.
        tags (DictType): Tags to apply to all resources.
        targets (ListType): Stag grouping.
        template_indent (StringType): Spaces to use per-indent level when
            outputing a template to json.

    """

    cfngin_bucket = StringType(serialize_when_none=False)
    cfngin_bucket_region = StringType(serialize_when_none=False)
    cfngin_cache_dir = StringType(serialize_when_none=False)
    log_formats = DictType(StringType, serialize_when_none=False)
    lookups = DictType(StringType, serialize_when_none=False)
    mappings = DictType(DictType(DictType(StringType)), serialize_when_none=False)
    namespace = StringType(required=True)
    namespace_delimiter = StringType(serialize_when_none=False)
    package_sources = ModelType(PackageSources, serialize_when_none=False)
    persistent_graph_key = StringType(serialize_when_none=False)
    post_build = ListType(ModelType(Hook), serialize_when_none=False)
    post_destroy = ListType(ModelType(Hook), serialize_when_none=False)
    pre_build = ListType(ModelType(Hook), serialize_when_none=False)
    pre_destroy = ListType(ModelType(Hook), serialize_when_none=False)
    service_role = StringType(serialize_when_none=False)
    stacker_bucket = StringType(serialize_when_none=False)
    stacker_bucket_region = StringType(serialize_when_none=False)
    stacker_cache_dir = StringType(serialize_when_none=False)
    stacks = ListType(ModelType(Stack), default=[])
    sys_path = StringType(serialize_when_none=False)
    tags = DictType(StringType, serialize_when_none=False)
    targets = ListType(ModelType(Target), serialize_when_none=False)
    template_indent = StringType(serialize_when_none=False)

    def __init__(
        self,
        raw_data=None,
        trusted_data=None,
        deserialize_mapping=None,
        init=True,
        partial=True,
        strict=True,
        validate=False,
        app_data=None,
        lazy=False,
        **kwargs
    ):
        """Extend functionality of the parent class.

        Manipulation here allows us to _clone_ the values of legacy stacker
        field into their new names. Doing so we can retain support for Stacker
        configs and CFNgin configs.

        """
        if raw_data:  # this can be empty when running unittests
            for field_suffix in ["bucket", "bucket_region", "cache_dir"]:
                cfngin_field = "cfngin_" + field_suffix
                stacker_field = "stacker_" + field_suffix
                # explicitly check for an empty string since it has specific logic.
                # cfngin fields with a value take precedence.
                if not (
                    raw_data.get(cfngin_field) or raw_data.get(cfngin_field) == ""
                ) and (
                    raw_data.get(stacker_field) or raw_data.get(stacker_field) == ""
                ):
                    raw_data[cfngin_field] = raw_data[stacker_field]
        super(Config, self).__init__(
            raw_data=raw_data,
            trusted_data=trusted_data,
            deserialize_mapping=deserialize_mapping,
            init=init,
            partial=partial,
            strict=strict,
            validate=validate,
            app_data=app_data,
            lazy=lazy,
            **kwargs
        )

    def _remove_excess_keys(self, data):
        excess_keys = set(data.keys())
        # attribute is defined in __new__ of base class
        excess_keys -= self._schema.valid_input_keys  # pylint: disable=no-member
        if not excess_keys:
            return data

        LOGGER.debug("removing excess keys from config: %s", excess_keys)
        clean_data = data.copy()
        for key in excess_keys:
            del clean_data[key]

        return clean_data

    def _convert(self, raw_data=None, context=None, **kwargs):
        if raw_data is not None:
            # Remove excess top-level keys, since we want to allow them to be
            # used for custom user variables to be reference later. This is
            # preferable to just disabling strict mode, as we can still
            # disallow excess keys in the inner models.
            raw_data = self._remove_excess_keys(raw_data)

        return super(Config, self)._convert(
            raw_data=raw_data, context=context, **kwargs
        )

    def validate(self, partial=False, convert=True, app_data=None, **kwargs):
        """Validate the state of the model.

        If the data is invalid, raises a ``DataError`` with error messages.

        Args:
            partial (bool): Allow partial data to validate. Essentially drops
                the ``required=True`` settings from field definitions.
            convert (bool): Controls whether to perform import conversion
                before validating. Can be turned off to skip an unnecessary
                conversion step if all values are known to have the right
                datatypes (e.g., when validating immediately after the initial
                import).

        Raises:
            UndefinedValueError
            SchematicsError

        """
        try:
            return super(Config, self).validate(partial, convert, app_data, **kwargs)
        except UndefinedValueError as err:
            raise exceptions.InvalidConfig([str(err)])
        except SchematicsError as err:
            raise exceptions.InvalidConfig(err.errors)

    def validate_stacker_bucket(self, _data, value):  # pylint: disable=no-self-use
        """Validate stack_bucket is not used.

        If in use, show deprecation warning.

        """
        msg = "stacker_bucket has been deprecated; use cfngin_bucket instead"
        if value or value == "":
            warnings.warn(msg, DeprecationWarning)
            LOGGER.warning(msg)

    def validate_stacker_bucket_region(  # pylint: disable=no-self-use
        self, _data, value
    ):
        """Validate stacker_bucket_regio is not used.

        If in use, show deprecation warning.

        """
        msg = (
            "stacker_bucket_region has been deprecated; use "
            "cfngin_bucket_region instead"
        )
        if value:
            warnings.warn(msg, DeprecationWarning)
            LOGGER.warning(msg)

    def validate_stacker_cache_dir(self, _data, value):  # pylint: disable=no-self-use
        """Validate stacker_cache_dir is not used.

        If in use, show deprecation warning.

        """
        msg = "stacker_cache_dir has been deprecated; use cfngin_cache_dir instead"
        if value:
            warnings.warn(msg, DeprecationWarning)
            LOGGER.warning(msg)

    def validate_stacks(self, _data, value):  # pylint: disable=no-self-use
        """Validate stacks."""
        if value:
            stack_names = [stack.name for stack in value]
            if len(set(stack_names)) != len(stack_names):
                # only loop / enumerate if there is an issue.
                for i, stack_name in enumerate(stack_names):
                    if stack_names.count(stack_name) != 1:
                        raise ValidationError(
                            "Duplicate stack %s found at index %d." % (stack_name, i)
                        )
