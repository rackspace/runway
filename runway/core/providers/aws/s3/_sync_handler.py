"""S3 sync handler."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union

from .....compat import cached_property
from ._helpers.action_architecture import ActionArchitecture
from ._helpers.parameters import Parameters, ParametersDataModel
from ._helpers.sync_strategy.register import register_sync_strategies
from ._helpers.transfer_config import RuntimeConfig

if TYPE_CHECKING:
    import boto3
    from mypy_boto3_s3.client import S3Client

    from .....context import CfnginContext, RunwayContext
    from ._helpers.transfer_config import TransferConfigDict


class S3SyncHandler:
    """S3 sync handler."""

    def __init__(
        self,
        context: Union[CfnginContext, RunwayContext],
        *,
        delete: bool = False,
        dest: str,
        exclude: Optional[List[str]] = None,
        follow_symlinks: bool = False,
        include: Optional[List[str]] = None,
        page_size: Optional[int] = None,
        session: Optional[boto3.Session] = None,
        src: str,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway or CFNgin context object.
            delete: If true, files that exist in the destination but not in the
                source are deleted.
            dest: Destination path.
            exclude: List of patterns for files/objects to exclude.
            follow_symlinks: If symlinks should be followed.
            include: List of patterns for files/objects to explicitly include.
            page_size: Number of items per page.
            session: boto3 Session.
            src: Source path.

        """
        self._session = session or context.get_session(region=context.env.aws_region)
        self._botocore_session = self._session._session
        self.ctx = context
        self.instructions = [
            "file_generator",
            "comparator",
            "file_info_builder",
            "s3_handler",
        ]
        self.parameters = Parameters(
            "sync",
            ParametersDataModel(
                delete=delete,
                dest=dest,
                exclude=exclude or [],
                follow_symlinks=follow_symlinks,
                include=include or [],
                page_size=page_size,
                src=src,
            ),
        )

    @cached_property
    def client(self) -> S3Client:
        """S3 client."""
        return self._session.client("s3")

    @cached_property
    def transfer_config(self) -> TransferConfigDict:
        """Get runtime transfer config."""
        return RuntimeConfig.build_config(
            **self._botocore_session.get_scoped_config().get("s3", {})
        )

    def run(self) -> None:
        """Run sync."""
        register_sync_strategies(self._botocore_session)
        ActionArchitecture(
            session=self._session,
            botocore_session=self._botocore_session,
            action="sync",
            parameters=self.parameters.data,
            runtime_config=self.transfer_config,
        ).run()
