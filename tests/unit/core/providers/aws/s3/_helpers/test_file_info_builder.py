"""Test runway.core.providers.aws.s3._helpers.file_info_builder."""

from __future__ import annotations

from mock import Mock

from runway.core.providers.aws.s3._helpers.file_generator import FileStats
from runway.core.providers.aws.s3._helpers.file_info import FileInfo
from runway.core.providers.aws.s3._helpers.file_info_builder import FileInfoBuilder
from runway.core.providers.aws.s3._helpers.parameters import ParametersDataModel


class TestFileInfoBuilder:
    """Test FileInfoBuilder."""

    def test_call_delete(self) -> None:
        """Test call delete."""
        client = Mock()
        source_client = Mock()
        builder = FileInfoBuilder(
            client=client,
            source_client=source_client,
            parameters=ParametersDataModel(dest="", src="", delete=True),
        )
        file_stats = FileStats(
            src="src",
            dest="dest",
            compare_key="compare_key",
            size=10,
            operation_name="delete",
        )
        results = list(builder.call([file_stats]))
        assert len(results) == 1
        result = results[0]
        assert result.client == source_client
        assert result.source_client == client

    def test_call_inject_info(self) -> None:
        """Test call _inject_info."""
        client = Mock()
        builder = FileInfoBuilder(client=client)
        file_stats = FileStats(
            src="src",
            dest="dest",
            compare_key="compare_key",
            size=10,
            operation_name="operation_name",
        )
        results = list(builder.call([file_stats]))
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, FileInfo)
        assert result.src == file_stats.src
        assert result.dest == file_stats.dest
        assert result.compare_key == file_stats.compare_key
        assert result.size == file_stats.size
        assert result.operation_name == file_stats.operation_name
        assert result.client == client
