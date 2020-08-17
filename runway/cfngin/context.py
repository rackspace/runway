"""CFNgin context."""
import collections
import json
import logging

from runway._logging import PrefixAdaptor

from .config import Config
from .exceptions import (
    PersistentGraphCannotLock,
    PersistentGraphCannotUnlock,
    PersistentGraphLockCodeMissmatch,
    PersistentGraphLocked,
    PersistentGraphUnlocked,
)
from .plan import Graph
from .session_cache import get_session
from .stack import Stack
from .target import Target
from .util import ensure_s3_bucket

LOGGER = logging.getLogger(__name__)


DEFAULT_NAMESPACE_DELIMITER = "-"
DEFAULT_TEMPLATE_INDENT = 4


def get_fqn(base_fqn, delimiter, name=None):
    """Return the fully qualified name of an object within this context.

    If the name passed already appears to be a fully qualified name, it
    will be returned with no further processing.

    """
    if name and name.startswith("%s%s" % (base_fqn, delimiter)):
        return name

    return delimiter.join([_f for _f in [base_fqn, name] if _f])


class Context(object):
    """The context under which the current stacks are being executed.

    The CFNgin Context is responsible for translating the values passed in
    via the command line and specified in the config to `Stack` objects.

    """

    def __init__(
        self,
        environment=None,
        boto3_credentials=None,
        stack_names=None,
        config=None,
        config_path=None,
        region=None,
        force_stacks=None,
    ):
        """Instantiate class.

        Args:
            boto3_credentials (Optional[Dict[str, str]]): Credentials to use
                when creating a boto3 session from context.
            environment (dict): A dictionary used to pass in information about
                the environment. Useful for templating.
            stack_names (list): A list of stack_names to operate on. If not
                passed, usually all stacks defined in the config will be
                operated on.
            config (:class:`runway.cfngin.config.Config`): The CFNgin
                configuration being operated on.
            config_path (str): Path to the config file that was provided.
            region (str): Name of an AWS region if provided as a CLI argument.
            force_stacks (list): A list of stacks to force work on. Used to
                work on locked stacks.

        """
        self.__boto3_credentials = boto3_credentials
        self._bucket_name = None
        self._persistent_graph = None
        self._persistent_graph_lock_code = None
        self._persistent_graph_lock_tag = "cfngin_lock_code"
        self._s3_bucket_verified = None
        self._stacks = None
        self._targets = None
        self._upload_to_s3 = None
        # TODO load the config from context instead of taking it as an arg
        self.config = config or Config()
        # TODO set this value when provisioning a Config object in context
        # set to a fake location for the time being but this should be set
        # by all runtime entry points. the only time the fake value should be
        # used is during tests.
        self.config_path = config_path or "./"
        self.bucket_region = self.config.cfngin_bucket_region or region
        self.environment = environment
        self.force_stacks = force_stacks or []
        self.hook_data = {}  # TODO change to MutableMap in next major release
        self.logger = PrefixAdaptor(config_path, LOGGER)
        self.region = region
        self.s3_conn = self.get_session(region=self.bucket_region).client("s3")
        self.stack_names = stack_names or []

    @property
    def _base_fqn(self):
        """Return ``namespace`` sanitized for use as an S3 Bucket name."""
        return self.namespace.replace(".", "-").lower()

    @property
    def _persistent_graph_tags(self):
        """Cache of tags on the persistent graph object.

        Returns:
            Dict[str, str]

        """
        try:
            return {
                t["Key"]: t["Value"]
                for t in self.s3_conn.get_object_tagging(
                    **self.persistent_graph_location
                ).get("TagSet", {})
            }
        except self.s3_conn.exceptions.NoSuchKey:
            self.logger.debug(
                "persistant graph object does not exist in S3; could not get tags"
            )
            return {}

    @property
    def bucket_name(self):
        """Return ``cfngin_bucket`` from config, calculated name, or None."""
        if not self.upload_to_s3:
            return None

        return self.config.cfngin_bucket or "stacker-%s" % (self.get_fqn(),)

    @property
    def mappings(self):
        """Return ``mappings`` from config."""
        return self.config.mappings or {}

    @property
    def namespace(self):
        """Return ``namespace`` from config."""
        return self.config.namespace

    @property
    def namespace_delimiter(self):
        """Return ``namespace_delimiter`` from config or default."""
        delimiter = self.config.namespace_delimiter
        if delimiter is not None:
            return delimiter
        return DEFAULT_NAMESPACE_DELIMITER

    @property
    def persistent_graph(self):
        """Graph if a persistent graph is being used.

        Will create an "empty" object in S3 if one is not found.

        Returns:
            :class:`runway.cfngin.plan.Graph`

        """
        if not self._persistent_graph:
            if not self.persistent_graph_location:
                return None

            content = "{}"

            if self.s3_bucket_verified:
                try:
                    self.logger.debug(
                        "getting persistent graph from s3:\n%s",
                        json.dumps(self.persistent_graph_location, indent=4),
                    )
                    content = (
                        self.s3_conn.get_object(
                            ResponseContentType="application/json",
                            **self.persistent_graph_location
                        )["Body"]
                        .read()
                        .decode("utf-8")
                    )
                except self.s3_conn.exceptions.NoSuchKey:
                    self.logger.info(
                        "persistant graph object does not exist in s3; "
                        "creating one now..."
                    )
                    self.s3_conn.put_object(
                        Body=content,
                        ServerSideEncryption="AES256",
                        ACL="bucket-owner-full-control",
                        ContentType="application/json",
                        **self.persistent_graph_location
                    )
            self.persistent_graph = json.loads(content)

        return self._persistent_graph

    @persistent_graph.setter
    def persistent_graph(self, graph_dict):
        """Load a persistent graph dict as a :class:`runway.cfngin.plan.Graph`."""
        self._persistent_graph = Graph.from_dict(graph_dict, self)

    @property
    def persistent_graph_location(self):
        """Location of the persistent graph in s3.

        Returns:
            Dict[str, str] Bucket and Key for the object in S3.

        """
        if not self.upload_to_s3 or not self.config.persistent_graph_key:
            return {}

        return {
            "Bucket": self.bucket_name,
            "Key": "persistent_graphs/{namespace}/{key}".format(
                namespace=self.config.namespace,
                key=(
                    self.config.persistent_graph_key + ".json"
                    if not self.config.persistent_graph_key.endswith(".json")
                    else self.config.persistent_graph_key
                ),
            ),
        }

    @property
    def persistent_graph_lock_code(self):
        """Code used to lock the persistent graph S3 object.

        Returns:
            Optional[str]

        """
        if not self._persistent_graph_lock_code and self.persistent_graph_location:
            self._persistent_graph_lock_code = self._persistent_graph_tags.get(
                self._persistent_graph_lock_tag
            )
        return self._persistent_graph_lock_code

    @property
    def persistent_graph_locked(self):
        """Check if persistent graph is locked.

        Returns:
            bool

        """
        if not self.persistent_graph:
            return False
        if not self.persistent_graph_lock_code:
            return False
        return True

    @property
    def s3_bucket_verified(self):
        """Check CFNgin bucket exists and you have access.

        If the CFNgin bucket does not exist, will try to create one.

        Returns:
            bool

        """
        if not self._s3_bucket_verified and self.bucket_name:
            ensure_s3_bucket(
                self.s3_conn,
                self.bucket_name,
                self.bucket_region,
                persist_graph=bool(self.persistent_graph_location),
            )
            self._s3_bucket_verified = True
        return self._s3_bucket_verified

    @property
    def tags(self):
        """Return ``tags`` from config."""
        tags = self.config.tags
        if tags is not None:
            return tags
        if self.namespace:
            return {"cfngin_namespace": self.namespace}
        return {}

    @property
    def template_indent(self):
        """Return ``template_indent`` from config or default."""
        indent = self.config.template_indent
        if indent is not None:
            return int(indent)
        return DEFAULT_TEMPLATE_INDENT

    @property
    def upload_to_s3(self):
        """Check if S3 should be used for caching/persistent graph.

        Returns:
            (bool)

        """
        if not self._upload_to_s3:
            # Don't upload stack templates to S3 if `cfngin_bucket` is
            # explicitly set to an empty string.
            if self.config.cfngin_bucket == "":
                self.logger.debug(
                    "not uploading to s3; cfngin_bucket "
                    "is explicitly set to an empty string"
                )
                return False

            # If no namespace is specificied, and there's no explicit
            # cfngin bucket specified, don't upload to s3. This makes
            # sense because we can't realistically auto generate a cfngin
            # bucket name in this case.
            if not self.namespace and not self.config.cfngin_bucket:
                self.logger.debug(
                    "not uploading to s3; namespace & cfngin_bucket not provided"
                )
                return False

        return True

    def _get_stack_definitions(self):
        """Return ``stacks`` from config."""
        return self.config.stacks

    def get_targets(self):
        """Return the named targets that are specified in the config.

        Returns:
            list: a list of :class:`runway.cfngin.target.Target` objects

        """
        if not self._targets:
            targets = []
            for target_def in self.config.targets or []:
                target = Target(target_def)
                targets.append(target)
            self._targets = targets
        return self._targets

    def get_session(self, profile=None, region=None):
        """Create a thread-safe boto3 session.

        Args:
            profile (Optional[str]): The profile for the session.
            region (Optional[str]): The region for the session.

        Returns:
            :class:`boto3.session.Session`: A thread-safe boto3 session.

        """
        kwargs = {}
        if profile:
            kwargs["profile"] = profile
        elif self.__boto3_credentials:
            kwargs.update(
                {
                    "access_key": self.__boto3_credentials.get("aws_access_key_id"),
                    "secret_key": self.__boto3_credentials.get("aws_secret_access_key"),
                    "session_token": self.__boto3_credentials.get("aws_session_token"),
                }
            )
        return get_session(region=region or self.region, **kwargs)

    def get_stack(self, name):
        """Get a stack by name.

        Args:
            name (str): Name of a stack to retrieve.

        """
        for stack in self.get_stacks():
            if stack.name == name:
                return stack
        return None

    def get_stacks(self):
        """Get the stacks for the current action.

        Handles configuring the :class:`runway.cfngin.stack.Stack` objects
        that will be used in the current action.

        Returns:
            list: a list of :class:`runway.cfngin.stack.Stack` objects

        """
        if not self._stacks:
            stacks = []
            definitions = self._get_stack_definitions()
            for stack_def in definitions:
                stack = Stack(
                    definition=stack_def,
                    context=self,
                    mappings=self.mappings,
                    force=stack_def.name in self.force_stacks,
                    locked=stack_def.locked,
                    enabled=stack_def.enabled,
                    protected=stack_def.protected,
                )
                stacks.append(stack)
            self._stacks = stacks
        return self._stacks

    def get_stacks_dict(self):
        """Construct a dict of {stack.fqn: stack} for easy access to stacks."""
        return dict((stack.fqn, stack) for stack in self.get_stacks())

    def get_fqn(self, name=None):
        """Return the fully qualified name of an object within this context.

        If the name passed already appears to be a fully qualified name, it
        will be returned with no further processing.

        """
        return get_fqn(self._base_fqn, self.namespace_delimiter, name)

    def lock_persistent_graph(self, lock_code):
        """Locks the persistent graph in s3.

        Args:
            lock_code (str): The code that will be used to lock the S3 object.

        Raises:
            :class:`runway.cfngin.exceptions.PersistentGraphLocked`
            :class:`runway.cfngin.exceptions.PersistentGraphCannotLock`

        """
        if not self.persistent_graph:
            return

        if self.persistent_graph_locked:
            raise PersistentGraphLocked

        try:
            self.s3_conn.put_object_tagging(
                Tagging={
                    "TagSet": [
                        {"Key": self._persistent_graph_lock_tag, "Value": lock_code}
                    ]
                },
                **self.persistent_graph_location
            )
            self.logger.info(
                'locked persistent graph "%s" with lock ID "%s"',
                "/".join(
                    [
                        self.persistent_graph_location["Bucket"],
                        self.persistent_graph_location["Key"],
                    ]
                ),
                lock_code,
            )
        except self.s3_conn.exceptions.NoSuchKey:
            raise PersistentGraphCannotLock("s3 object does not exist")

    def put_persistent_graph(self, lock_code):
        """Upload persistent graph to s3.

        Args:
            lock_code (str): The code that will be used to lock the S3 object.

        Raises:
            :class:`runway.cfngin.exceptions.PersistentGraphUnlocked`
            :class:`runway.cfngin.exceptions.PersistentGraphLockCodeMissmatch`

        """
        if not self.persistent_graph:
            return

        if not self.persistent_graph.to_dict():
            self.s3_conn.delete_object(**self.persistent_graph_location)
            self.logger.debug("removed empty persistent graph object from S3")
            return

        if not self.persistent_graph_locked:
            raise PersistentGraphUnlocked(
                reason="It must be locked by the current session to be updated."
            )

        if self.persistent_graph_lock_code != lock_code:
            raise PersistentGraphLockCodeMissmatch(
                lock_code, self.persistent_graph_lock_code
            )

        self.s3_conn.put_object(
            Body=self.persistent_graph.dumps(4),
            ServerSideEncryption="AES256",
            ACL="bucket-owner-full-control",
            ContentType="application/json",
            Tagging="{}={}".format(self._persistent_graph_lock_tag, lock_code),
            **self.persistent_graph_location
        )
        self.logger.debug(
            "persistent graph updated:\n%s", self.persistent_graph.dumps(indent=4)
        )

    def set_hook_data(self, key, data):
        """Set hook data for the given key.

        Args:
            key(str): The key to store the hook data in.
            data(:class:`collections.Mapping`): A dictionary of data to store,
                as returned from a hook.

        """
        if not isinstance(data, collections.Mapping):
            raise ValueError(
                "Hook (key: %s) data must be an instance of "
                "collections.Mapping (a dictionary for example)." % key
            )

        if key in self.hook_data:
            raise KeyError(
                "Hook data for key %s already exists, each hook "
                "must have a unique data_key." % key
            )

        self.hook_data[key] = data

    def unlock_persistent_graph(self, lock_code):
        """Unlocks the persistent graph in s3.

        Args:
            lock_code (str): The code that will be used to lock the S3 object.

        Raises:
            :class:`runway.cfngin.exceptions.PersistentGraphCannotUnlock`

        """
        if not self.persistent_graph:
            return True

        if not self.persistent_graph.to_dict():
            try:
                self.s3_conn.get_object(
                    ResponseContentType="application/json",
                    **self.persistent_graph_location
                )
            except self.s3_conn.exceptions.NoSuchKey:
                self.logger.info(
                    "persistent graph deleted; does not need to be unlocked"
                )
                return True

        self.logger.verbose(
            'unlocking persistent graph "%s"...', self.persistent_graph_location
        )

        if not self.persistent_graph_locked:
            raise PersistentGraphCannotUnlock(
                PersistentGraphUnlocked(
                    reason="It must be locked by the current session to be unlocked."
                )
            )

        if self.persistent_graph_lock_code == lock_code:
            try:
                self.s3_conn.delete_object_tagging(**self.persistent_graph_location)
            except self.s3_conn.exceptions.NoSuchKey:
                pass
            self._persistent_graph_lock_code = None
            self.logger.info(
                'unlocked persistent graph "%s"',
                "/".join(
                    [
                        self.persistent_graph_location["Bucket"],
                        self.persistent_graph_location["Key"],
                    ]
                ),
            )
            return True
        raise PersistentGraphCannotUnlock(
            PersistentGraphLockCodeMissmatch(lock_code, self.persistent_graph_lock_code)
        )
