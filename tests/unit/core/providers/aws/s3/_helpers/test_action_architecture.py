"""Test runway.core.providers.aws.s3._helpers.action_architecture."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import Mock, call

import pytest

from runway.core.providers.aws.s3._helpers.action_architecture import ActionArchitecture
from runway.core.providers.aws.s3._helpers.parameters import ParametersDataModel
from runway.core.providers.aws.s3._helpers.transfer_config import RuntimeConfig

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.core.providers.aws.s3._helpers.transfer_config import TransferConfigDict

    from .conftest import LocalFiles

MODULE = "runway.core.providers.aws.s3._helpers.action_architecture"


class TestActionArchitecture:
    """Test ActionArchitecture."""

    action: ActionArchitecture
    boto3_session: Mock
    botocore_session: Mock
    client: Mock
    parameters: ParametersDataModel
    runtime_config: TransferConfigDict

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.client = Mock()
        self.boto3_session = Mock(client=Mock(return_value=self.client))
        self.botocore_session = Mock()
        self.parameters = ParametersDataModel(src="src", dest="dest")
        self.runtime_config = RuntimeConfig.defaults()
        self.action = ActionArchitecture(
            session=self.boto3_session,
            botocore_session=self.botocore_session,
            action="sync",
            parameters=self.parameters,
            runtime_config=self.runtime_config,
        )

    def test_choose_sync_strategies(self, mocker: MockerFixture) -> None:
        """Test choose_sync_strategies."""
        mock_missing = mocker.patch(f"{MODULE}.MissingFileSync")
        mock_never = mocker.patch(f"{MODULE}.NeverSync")
        mock_size = mocker.patch(f"{MODULE}.SizeAndLastModifiedSync")
        self.botocore_session.emit.return_value = None
        assert self.action.choose_sync_strategies() == {
            "file_at_src_and_dest_sync_strategy": mock_size.return_value,
            "file_not_at_dest_sync_strategy": mock_missing.return_value,
            "file_not_at_src_sync_strategy": mock_never.return_value,
        }
        self.botocore_session.emit.assert_called_once_with(
            "choosing-s3-sync-strategy", params=self.parameters
        )

    def test_choose_sync_strategies_add_another(self, mocker: MockerFixture) -> None:
        """Test choose_sync_strategies."""
        new_sync_strategy = Mock(sync_type="new")
        mock_missing = mocker.patch(f"{MODULE}.MissingFileSync")
        mock_never = mocker.patch(f"{MODULE}.NeverSync")
        mock_size = mocker.patch(f"{MODULE}.SizeAndLastModifiedSync")
        self.botocore_session.emit.return_value = [(None, new_sync_strategy)]
        assert self.action.choose_sync_strategies() == {
            "file_at_src_and_dest_sync_strategy": mock_size.return_value,
            "file_not_at_dest_sync_strategy": mock_missing.return_value,
            "file_not_at_src_sync_strategy": mock_never.return_value,
            "new_sync_strategy": new_sync_strategy,
        }

    def test_client(self) -> None:
        """Test client."""
        assert self.action.client == self.client
        self.boto3_session.client.assert_called_once_with("s3")

    def test_instructions(self) -> None:
        """Test instructions."""
        assert self.action.instructions == [
            "file_generator",
            "comparator",
            "file_info_builder",
            "s3_handler",
        ]

    def test_instructions_exclude(self) -> None:
        """Test instructions."""
        self.parameters.exclude = ["something"]
        assert self.action.instructions == [
            "file_generator",
            "filters",
            "comparator",
            "file_info_builder",
            "s3_handler",
        ]

    def test_instructions_filters(self) -> None:
        """Test instructions."""
        self.parameters.exclude = ["something"]
        self.parameters.include = ["something"]
        assert self.action.instructions == [
            "file_generator",
            "filters",
            "comparator",
            "file_info_builder",
            "s3_handler",
        ]

    def test_instructions_include(self) -> None:
        """Test instructions."""
        self.parameters.include = ["something"]
        assert self.action.instructions == [
            "file_generator",
            "filters",
            "comparator",
            "file_info_builder",
            "s3_handler",
        ]

    @pytest.mark.parametrize(
        "num_tasks_failed, num_tasks_warned, expected",
        [(0, 0, 0), (5, 0, 1), (0, 5, 2), (5, 5, 1)],
    )
    def test_run_sync(
        self,
        expected: int,
        loc_files: LocalFiles,
        mocker: MockerFixture,
        num_tasks_failed: int,
        num_tasks_warned: int,
    ) -> None:
        """Test run."""
        self.parameters.exclude = ["something"]
        files = {"type": "files"}
        rev_files = {"type": "rev_files"}
        mocker.patch.object(
            ActionArchitecture,
            "choose_sync_strategies",
            return_value={"sync_strategy": "test"},
        )
        mocker.patch(f"{MODULE}.FormatPath", format=Mock(side_effect=[files, rev_files]))
        mock_file_generator = Mock(call=Mock(return_value="FileGenerator().call()"))
        mock_file_generator_rev = Mock(call=Mock(return_value="rev:FileGenerator().call()"))
        mock_file_info_builder = Mock(call=Mock(return_value="FileInfoBuilder().call()"))
        mock_comparator = Mock(call=Mock(return_value="Comparator().call()"))
        mocker.patch(f"{MODULE}.Comparator", return_value=mock_comparator)
        mocker.patch(
            f"{MODULE}.FileGenerator",
            side_effect=[mock_file_generator, mock_file_generator_rev],
        )
        mocker.patch(f"{MODULE}.FileInfoBuilder", return_value=mock_file_info_builder)
        mock_filter_inst = Mock(call=Mock(return_value="Filter.call()"))
        mock_filter_class = mocker.patch(
            f"{MODULE}.Filter", parse_params=Mock(return_value=mock_filter_inst)
        )
        mock_s3_transfer_handler = Mock(
            call=Mock(
                return_value=Mock(
                    num_tasks_failed=num_tasks_failed, num_tasks_warned=num_tasks_warned
                )
            )
        )
        mocker.patch(
            f"{MODULE}.S3TransferHandlerFactory",
            return_value=Mock(return_value=mock_s3_transfer_handler),
        )
        self.parameters.src = f"{loc_files['tmp_path']}{os.sep}"
        self.parameters.dest = "s3://bucket/"
        self.parameters.paths_type = "locals3"
        assert self.action.run() == expected
        mock_file_generator.call.assert_called_once_with(files)
        mock_file_generator_rev.call.assert_called_once_with(rev_files)
        mock_filter_class.parse_params.assert_has_calls(
            [call(self.parameters), call(self.parameters)]
        )
        mock_filter_inst.call.assert_has_calls(
            [
                call(mock_file_generator.call.return_value),
                call(mock_file_generator_rev.call.return_value),
            ]
        )
        mock_comparator.call.assert_called_once_with(
            mock_filter_inst.call.return_value, mock_filter_inst.call.return_value
        )
        mock_file_info_builder.call.assert_called_once_with(mock_comparator.call.return_value)
        mock_s3_transfer_handler.call.assert_called_once_with(
            mock_file_info_builder.call.return_value
        )

    def test_run_not_implimented(self, mocker: MockerFixture) -> None:
        """Test run NotImplimented."""
        mocker.patch.object(
            ActionArchitecture,
            "choose_sync_strategies",
            return_value={"sync_strategy": "test"},
        )
        self.action.action = "invalid"
        self.parameters.paths_type = "locals3"
        with pytest.raises(NotImplementedError):
            self.action.run()
