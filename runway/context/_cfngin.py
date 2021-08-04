"""CFNgin context."""
from __future__ import annotations

import collections.abc
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, MutableMapping, Optional, Union, cast

from pydantic import BaseModel

from .._logging import PrefixAdaptor, RunwayLogger
from ..cfngin.exceptions import (
    PersistentGraphCannotLock,
    PersistentGraphCannotUnlock,
    PersistentGraphLockCodeMissmatch,
    PersistentGraphLocked,
    PersistentGraphUnlocked,
)
from ..cfngin.plan import Graph
from ..cfngin.stack import Stack
from ..cfngin.utils import ensure_s3_bucket
from ..compat import cached_property
from ..config import CfnginConfig
from ..core.components import DeployEnvironment
from ._base import BaseContext

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

    from .type_defs import PersistentGraphLocation

LOGGER = cast(RunwayLogger, logging.getLogger(__name__))


def get_fqn(base_fqn: str, delimiter: str, name: Optional[str] = None) -> str:
    """Return the fully qualified name of an object within this context.

    If the name passed already appears to be a fully qualified name, it
    will be returned with no further processing.

    """
    if name and name.startswith(f"{base_fqn}{delimiter}"):
        return name

    return delimiter.join([_f for _f in [base_fqn, name] if _f])


class CfnginContext(BaseContext):
    """CFNgin context object.

    Attributes:
        bucket_region: Region where the S3 Bucket is located. The S3 Bucket
            being the Bucket configured for staging CloudFormation Templates.
        config: CFNgin configuration file that has been resolved & parsed into a
            python object.
        config_path: Path to the configuration file that has been resolved, parsed
            and made accessable via this object.
        env: Deploy environment object containing information about the current
            deploy environment.
        force_stacks: List of stacks to force.
        hook_data: Values returned by hooks that are stored based on the ``data_key``
            defined for the hook. Returned values are only stored if a ``data_key``
            was provided AND the return value is a dict or ``pydantic.BaseModel``.
        logger: Custom logger to use when logging messages.
        parameters: Parameters passed from Runway or read from a file.
        stack_names: List of Stack names to operate on. If value is falsy, all
            Stacks defined in the config will be operated on.

    """

    _persistent_graph_lock_code: Optional[str]
    _persistent_graph_lock_tag: str = "cfngin_lock_code"
    _persistent_graph: Optional[Graph]
    _s3_bucket_verified: bool

    bucket_region: str
    config: CfnginConfig
    config_path: Path
    env: DeployEnvironment
    force_stacks: List[str]
    hook_data: Dict[str, Any]
    logger: Union[PrefixAdaptor, RunwayLogger]
    parameters: MutableMapping[str, Any]
    stack_names: List[str]

    def __init__(
        self,
        *,
        config: Optional[CfnginConfig] = None,
        config_path: Optional[Path] = None,
        deploy_environment: Optional[DeployEnvironment] = None,
        force_stacks: Optional[List[str]] = None,
        logger: Union[PrefixAdaptor, RunwayLogger] = LOGGER,
        parameters: Optional[MutableMapping[str, Any]] = None,
        stack_names: Optional[List[str]] = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            config: The CFNgin configuration being operated on.
            config_path: Path to the config file that was provided.
            deploy_environment: The current deploy environment.
            force_stacks: A list of stacks to force work on. Used to work on locked stacks.
            logger: Custom logger.
            parameters: Parameters passed from Runway or read from a file.
            stack_names: A list of stack_names to operate on. If not passed,
                all stacks defined in the config will be operated on.

        """
        self.config_path = config_path or Path.cwd()
        super().__init__(
            deploy_environment=deploy_environment or DeployEnvironment(),
            logger=PrefixAdaptor(
                self.config_path.name.split(".")[0],
                logger if isinstance(logger, RunwayLogger) else LOGGER,
            ),
        )
        self._persistent_graph_lock_code = None
        self._persistent_graph = None
        self._s3_bucket_verified = False
        self.config = config or CfnginConfig.parse_obj({"namespace": "example"})
        self.bucket_region = self.config.cfngin_bucket_region or self.env.aws_region
        self.parameters = parameters or {}
        self.force_stacks = force_stacks or []
        self.hook_data = {}
        self.stack_names = stack_names or []

    @cached_property
    def base_fqn(self) -> str:
        """Return ``namespace`` sanitized for use as an S3 Bucket name."""
        return self.config.namespace.replace(".", "-").lower()

    @cached_property
    def bucket_name(self) -> Optional[str]:
        """Return ``cfngin_bucket`` from config, calculated name, or None."""
        if not self.upload_to_s3:
            return None
        return (
            self.config.cfngin_bucket
            or f"cfngin-{self.get_fqn()}-{self.env.aws_region}"
        )

    @cached_property
    def mappings(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Return ``mappings`` from config."""
        return self.config.mappings or {}

    @cached_property
    def namespace(self) -> str:
        """Return ``namespace`` from config."""
        return self.config.namespace

    @cached_property
    def namespace_delimiter(self) -> str:
        """Return ``namespace_delimiter`` from config or default."""
        return self.config.namespace_delimiter

    @cached_property
    def persistent_graph_location(self) -> PersistentGraphLocation:
        """Location of the persistent graph in s3."""
        if not self.bucket_name or not self.config.persistent_graph_key:
            return {}

        return {
            "Bucket": self.bucket_name,
            "Key": "persistent_graphs/{namespace}/{key}".format(  # noqa: FS002
                namespace=self.config.namespace,
                key=(
                    self.config.persistent_graph_key + ".json"
                    if not self.config.persistent_graph_key.endswith(".json")
                    else self.config.persistent_graph_key
                ),
            ),
        }

    @property
    def persistent_graph_locked(self) -> bool:
        """Check if persistent graph is locked."""
        if not self.persistent_graph:
            return False
        return bool(self.persistent_graph_lock_code)

    @property
    def persistent_graph_lock_code(self) -> Optional[str]:
        """Code used to lock the persistent graph S3 object."""
        if not self._persistent_graph_lock_code and self.persistent_graph_location:
            self._persistent_graph_lock_code = self.persistent_graph_tags.get(
                self._persistent_graph_lock_tag
            )
        return self._persistent_graph_lock_code

    @property
    def persistent_graph_tags(self) -> Dict[str, str]:
        """Cache of tags on the persistent graph object."""
        try:
            return {
                t["Key"]: t["Value"]
                for t in self.s3_client.get_object_tagging(
                    **self.persistent_graph_location
                ).get("TagSet", {})
            }
        except self.s3_client.exceptions.NoSuchKey:
            self.logger.debug(
                "persistant graph object does not exist in S3; could not get tags"
            )
            return {}

    @property
    def persistent_graph(self) -> Optional[Graph]:
        """Graph if a persistent graph is being used.

        Will create an "empty" object in S3 if one is not found.

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
                        self.s3_client.get_object(
                            ResponseContentType="application/json",
                            **self.persistent_graph_location,
                        )["Body"]
                        .read()
                        .decode("utf-8")
                    )
                except self.s3_client.exceptions.NoSuchKey:
                    self.logger.info(
                        "persistant graph object does not exist in s3; "
                        "creating one now..."
                    )
                    self.s3_client.put_object(
                        Body=content.encode(),
                        ServerSideEncryption="AES256",
                        ACL="bucket-owner-full-control",
                        ContentType="application/json",
                        **self.persistent_graph_location,
                    )
            self.persistent_graph = Graph.from_dict(json.loads(content), self)

        return self._persistent_graph

    @persistent_graph.setter
    def persistent_graph(self, graph: Optional[Graph]) -> None:
        """Load a persistent graph dict as a :class:`runway.cfngin.plan.Graph`."""
        self._persistent_graph = graph

    @property
    def s3_bucket_verified(self) -> bool:
        """Check CFNgin bucket exists and you have access.

        If the CFNgin bucket does not exist, will try to create one.

        """
        if not self._s3_bucket_verified and self.bucket_name:
            ensure_s3_bucket(
                self.s3_client,
                self.bucket_name,
                self.bucket_region,
                create=False,
                persist_graph=bool(self.persistent_graph_location),
            )
            self._s3_bucket_verified = True
        return bool(self._s3_bucket_verified)

    @cached_property
    def s3_client(self) -> S3Client:
        """AWS S3 client."""
        return self.get_session(region=self.bucket_region).client("s3")

    @cached_property
    def stacks_dict(self) -> Dict[str, Stack]:
        """Construct a dict of ``{stack.fqn: Stack}`` for easy access to stacks."""
        return {stack.fqn: stack for stack in self.stacks}

    @cached_property
    def stacks(self) -> List[Stack]:
        """Stacks for the current action."""
        return [
            Stack(
                context=self,
                definition=stack_def,
                enabled=stack_def.enabled,
                force=stack_def.name in self.force_stacks,
                locked=stack_def.locked,
                mappings=self.mappings,
                protected=stack_def.protected,
            )
            for stack_def in self.config.stacks
        ]

    @cached_property
    def tags(self) -> Dict[str, str]:
        """Return ``tags`` from config."""
        return (
            self.config.tags
            if self.config.tags is not None
            else {"cfngin_namespace": self.config.namespace}
            if self.config.namespace
            else {}
        )

    @cached_property
    def template_indent(self) -> int:
        """Return ``template_indent`` from config or default."""
        return self.config.template_indent

    @cached_property
    def upload_to_s3(self) -> bool:
        """Check if S3 should be used for caching/persistent graph."""
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
        if not self.config.namespace and not self.config.cfngin_bucket:
            self.logger.debug(
                "not uploading to s3; namespace & cfngin_bucket not provided"
            )
            return False

        return True

    def copy(self) -> CfnginContext:
        """Copy the contents of this object into a new instance."""
        return self.__class__(
            config_path=self.config_path,
            config=self.config,
            deploy_environment=self.env.copy(),
            force_stacks=self.force_stacks,
            logger=self.logger,
            parameters=self.parameters,
            stack_name=self.stack_names,
        )

    def get_fqn(self, name: Optional[str] = None) -> str:
        """Return the fully qualified name of an object within this context.

        If the name passed already appears to be a fully qualified name, it
        will be returned with no further processing.

        """
        return get_fqn(self.base_fqn, self.config.namespace_delimiter, name)

    def get_stack(self, name: str) -> Optional[Stack]:
        """Get a stack by name.

        Args:
            name: Name of a Stack as defined in the config.

        """
        return self.stacks_dict.get(self.get_fqn(name))

    def lock_persistent_graph(self, lock_code: str) -> None:
        """Locks the persistent graph in s3.

        Args:
            lock_code: The code that will be used to lock the S3 object.

        Raises:
            :class:`runway.cfngin.exceptions.PersistentGraphLocked`
            :class:`runway.cfngin.exceptions.PersistentGraphCannotLock`

        """
        if not self.persistent_graph:
            return

        if self.persistent_graph_locked:
            raise PersistentGraphLocked

        try:
            self.s3_client.put_object_tagging(
                Tagging={
                    "TagSet": [
                        {"Key": self._persistent_graph_lock_tag, "Value": lock_code}
                    ]
                },
                **self.persistent_graph_location,
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
        except self.s3_client.exceptions.NoSuchKey as exc:
            raise PersistentGraphCannotLock("s3 object does not exist") from exc

    def put_persistent_graph(self, lock_code: str) -> None:
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
            self.s3_client.delete_object(**self.persistent_graph_location)
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

        self.s3_client.put_object(
            Body=self.persistent_graph.dumps(4).encode(),
            ServerSideEncryption="AES256",
            ACL="bucket-owner-full-control",
            ContentType="application/json",
            Tagging=f"{self._persistent_graph_lock_tag}={lock_code}",
            **self.persistent_graph_location,
        )
        self.logger.debug(
            "persistent graph updated:\n%s", self.persistent_graph.dumps(indent=4)
        )

    def set_hook_data(self, key: str, data: Any) -> None:
        """Set hook data for the given key.

        Args:
            key: The key to store the hook data in.
            data: A dictionary of data to store, as returned from a hook.

        """
        if not isinstance(data, (BaseModel, collections.abc.Mapping)):
            raise TypeError(
                f"Hook data (key: {key}) must be an instance of "
                "collections.abc.Mapping (a dictionary for example) or pydantic.BaseModel."
            )

        if key in self.hook_data:
            raise KeyError(
                f"Hook data for key {key} already exists, each hook "
                "must have a unique data_key."
            )

        self.hook_data[key] = data

    def unlock_persistent_graph(self, lock_code: str) -> bool:
        """Unlocks the persistent graph in s3.

        Args:
            lock_code: The code that will be used to lock the S3 object.

        Raises:
            :class:`runway.cfngin.exceptions.PersistentGraphCannotUnlock`

        """
        if not self.persistent_graph:
            return True

        if not self.persistent_graph.to_dict():
            try:
                self.s3_client.get_object(
                    ResponseContentType="application/json",
                    **self.persistent_graph_location,
                )
            except self.s3_client.exceptions.NoSuchKey:
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
                self.s3_client.delete_object_tagging(**self.persistent_graph_location)
            except self.s3_client.exceptions.NoSuchKey:
                pass
            self._persistent_graph_lock_code = None
            self.logger.info(
                'unlocked persistent graph "%s/%s"',
                self.persistent_graph_location.get("Bucket"),
                self.persistent_graph_location.get("Key"),
            )
            return True
        raise PersistentGraphCannotUnlock(
            PersistentGraphLockCodeMissmatch(lock_code, self.persistent_graph_lock_code)
        )
