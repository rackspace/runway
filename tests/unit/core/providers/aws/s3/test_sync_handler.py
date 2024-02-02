"""Test runway.core.providers.aws.s3._sync_handler."""

# pylint: disable=protected-access
from __future__ import annotations

from typing import TYPE_CHECKING

from mock import Mock

from runway.core.providers.aws.s3._sync_handler import S3SyncHandler

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from .....factories import MockRunwayContext

MODULE = "runway.core.providers.aws.s3._sync_handler"


class TestS3SyncHandler:
    """Test S3SyncHandler."""

    def test_client(self, runway_context: MockRunwayContext) -> None:
        """Test client."""
        runway_context.add_stubber("s3")
        assert S3SyncHandler(
            runway_context, dest="", src=""
        ).client == runway_context.get_session().client("s3")

    def test_run(
        self, mocker: MockerFixture, runway_context: MockRunwayContext
    ) -> None:
        """Test run."""
        mock_register_sync_strategies = mocker.patch(
            f"{MODULE}.register_sync_strategies"
        )
        mock_action = mocker.patch(f"{MODULE}.ActionArchitecture")
        transfer_config = mocker.patch.object(
            S3SyncHandler, "transfer_config", {"key": "val"}
        )
        obj = S3SyncHandler(runway_context, dest="", src="")
        assert not obj.run()
        mock_register_sync_strategies.assert_called_once_with(obj._botocore_session)
        mock_action.assert_called_once_with(
            session=obj._session,
            botocore_session=obj._botocore_session,
            action="sync",
            parameters=obj.parameters.data,
            runtime_config=transfer_config,
        )
        mock_action().run.assert_called_once_with()

    def test_transfer_config(
        self, mocker: MockerFixture, runway_context: MockRunwayContext
    ) -> None:
        """Test transfer_config."""
        mock_runtime_config = mocker.patch(
            f"{MODULE}.RuntimeConfig", build_config=Mock(return_value="success")
        )
        config = {"key": "val"}
        scoped_config = Mock(get=Mock(return_value=config))
        obj = S3SyncHandler(runway_context, dest="", src="")
        obj._botocore_session.get_scoped_config = Mock(return_value=scoped_config)
        assert obj.transfer_config == mock_runtime_config.build_config.return_value
        obj._botocore_session.get_scoped_config.assert_called_once_with()
        scoped_config.get.assert_called_once_with("s3", {})
        mock_runtime_config.build_config.assert_called_once_with(**config)
