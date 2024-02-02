"""Test runway.cfngin.hooks.staticsite.utils."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Union, cast

import igittigitt
import pytest
from mock import Mock, call

from runway.cfngin.hooks.staticsite.utils import (
    calculate_hash_of_files,
    get_hash_of_files,
    get_ignorer,
)

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


@pytest.mark.parametrize(
    "directories", [None, [{"path": "./"}], [{"path": "./", "exclusions": ["foobar"]}]]
)
def test_get_hash_of_files(
    directories: Optional[List[Dict[str, Union[List[str], str]]]],
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Test get_hash_of_files."""
    gitignore = igittigitt.IgnoreParser()
    mock_calculate_hash_of_files = mocker.patch(
        f"{MODULE}.calculate_hash_of_files", return_value="success"
    )
    mock_get_ignorer = mocker.patch(f"{MODULE}.get_ignorer", return_value=gitignore)

    # files in root dir
    foo_file = tmp_path / "foo"
    foo_file.touch()
    (tmp_path / "foo.ignore").touch()

    # excluded dir
    exclude_dir = tmp_path / "exclude"
    exclude_dir.mkdir()
    (exclude_dir / "foo").touch()

    # included dir
    include_dir = tmp_path / "include"
    include_dir.mkdir()
    bar_file = include_dir / "bar"
    bar_file.touch()
    (include_dir / "foo.ignore").touch()

    gitignore.add_rule("**/*.ignore", tmp_path)
    gitignore.add_rule("exclude/", tmp_path)

    if directories:
        assert (
            get_hash_of_files(tmp_path, directories)
            == mock_calculate_hash_of_files.return_value
        )
    else:
        assert get_hash_of_files(tmp_path) == mock_calculate_hash_of_files.return_value
    mock_get_ignorer.assert_has_calls(
        [  # type: ignore
            call(tmp_path / cast(str, i["path"]), i.get("exclusions"))
            for i in (directories or [{"path": "./"}])
        ]
    )
    mock_calculate_hash_of_files.assert_called_once_with([foo_file, bar_file], tmp_path)


@pytest.mark.parametrize("additional_exclusions", [None, [], ["foo"], ["foo", "bar"]])
def test_get_ignorer(
    additional_exclusions: Optional[List[str]], mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test get_ignorer."""
    ignore_parser = mocker.patch(f"{MODULE}.igittigitt.IgnoreParser")
    ignore_parser.return_value = ignore_parser

    result = get_ignorer(tmp_path, additional_exclusions)
    assert result == ignore_parser
    ignore_parser.assert_called_once_with()
    ignore_parser.parse_rule_files.assert_called_once_with(tmp_path)

    if additional_exclusions:
        ignore_parser.add_rule.assert_has_calls(
            [call(i, tmp_path) for i in additional_exclusions]
        )
    else:
        ignore_parser.add_rule.assert_not_called()
