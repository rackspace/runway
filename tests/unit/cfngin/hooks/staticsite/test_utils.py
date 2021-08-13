"""Test runway.cfngin.hooks.staticsite.utils."""
from __future__ import annotations

from typing import TYPE_CHECKING

from mock import Mock

from runway.cfngin.hooks.staticsite.utils import calculate_hash_of_files

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

MODULE = "runway.cfngin.hooks.staticsite.utils"


def test_calculate_hash_of_files(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test calculate_hash_of_files."""
    mock_file_hash_obj = Mock(add_files=Mock(), hexdigest="success")
    mocker.patch(f"{MODULE}.FileHash", return_value=mock_file_hash_obj)

    file0 = tmp_path / "nested" / "file0.txt"
    file1 = tmp_path / "file1.txt"
    assert (
        calculate_hash_of_files([file0, file1], tmp_path)
        == mock_file_hash_obj.hexdigest
    )
    mock_file_hash_obj.add_files.assert_called_once_with(
        [str(file1), str(file0)], relative_to=tmp_path
    )
