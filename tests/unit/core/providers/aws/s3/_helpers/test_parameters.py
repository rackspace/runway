"""Test runway.core.providers.aws.s3._helpers.parameters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

import pytest
from pydantic import ValidationError

from runway.core.providers.aws.s3._helpers.parameters import (
    Parameters,
    ParametersDataModel,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from runway.core.providers.aws.s3._helpers.parameters import PathsType


class TestParameters:
    """Test Parameters."""

    data_locallocal: ParametersDataModel
    data_s3s3: ParametersDataModel
    data_s3local: ParametersDataModel

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.data_locallocal = ParametersDataModel(dest="test-dest", src="test-src")
        self.data_s3s3 = ParametersDataModel(dest="s3://test-dest", src="s3://test-src")
        self.data_s3local = ParametersDataModel(dest="test-dest", src="s3://test-src")

    def test_init(self, mocker: MockerFixture) -> None:
        """Test __init__."""
        mock_validate_path_args = mocker.patch.object(Parameters, "_validate_path_args")
        obj = Parameters("test", self.data_locallocal)
        assert obj.action == "test"
        assert obj.data == self.data_locallocal
        mock_validate_path_args.assert_called_once_with()

    @pytest.mark.parametrize(
        "cmd, expected",
        [("sync", True), ("mb", True), ("rb", True), ("cp", False), ("mv", False)],
    )
    def test_init_set_dir_op(self, cmd: str, expected: bool, mocker: MockerFixture) -> None:
        """Test __init__."""
        mocker.patch.object(Parameters, "_validate_path_args")
        assert Parameters(cmd, self.data_locallocal).data.dir_op == expected

    @pytest.mark.parametrize(
        "cmd, expected",
        [("sync", False), ("mb", False), ("rb", False), ("cp", False), ("mv", True)],
    )
    def test_init_set_is_move(self, cmd: str, expected: bool, mocker: MockerFixture) -> None:
        """Test __init__."""
        mocker.patch.object(Parameters, "_validate_path_args")
        assert Parameters(cmd, self.data_locallocal).data.is_move == expected

    def test_same_path_mv_locallocal(self) -> None:
        """Test _same_path."""
        self.data_locallocal.dest = self.data_locallocal.src
        assert Parameters("mv", self.data_locallocal)

    def test_same_path_mv_s3s3(self) -> None:
        """Test _same_path."""
        self.data_s3s3.dest = self.data_s3s3.src
        with pytest.raises(ValueError) as excinfo:
            Parameters("mv", self.data_s3s3)
        assert "Cannot mv a file onto itself" in str(excinfo.value)

    def test_same_path_mv_s3s3_not_same(self) -> None:
        """Test _same_path."""
        assert Parameters("mv", self.data_s3s3)

    def test_same_path_sync_locallocal(self) -> None:
        """Test _same_path."""
        self.data_locallocal.dest = self.data_locallocal.src
        assert Parameters("sync", self.data_locallocal)

    def test_same_path_sync_s3s3(self) -> None:
        """Test _same_path."""
        self.data_s3s3.dest = self.data_s3s3.src
        assert Parameters("sync", self.data_s3s3)

    def test_validate_path_args_mv_s3local(self, tmp_path: Path) -> None:
        """Test _validate_path_args."""
        self.data_s3local.dest = str(tmp_path)
        assert Parameters("mv", self.data_s3local)

    def test_validate_path_args_mv_s3local_not_exist(self, tmp_path: Path) -> None:
        """Test _validate_path_args."""
        missing_dir = tmp_path / "missing"
        self.data_s3local.dest = str(missing_dir)
        assert Parameters("mv", self.data_s3local)
        assert not missing_dir.exists()

    def test_validate_path_args_sync_s3local(self, tmp_path: Path) -> None:
        """Test _validate_path_args."""
        self.data_s3local.dest = str(tmp_path)
        assert Parameters("sync", self.data_s3local)

    def test_validate_path_args_sync_s3local_not_exist(self, tmp_path: Path) -> None:
        """Test _validate_path_args."""
        missing_dir = tmp_path / "missing"
        self.data_s3local.dest = str(missing_dir)
        assert Parameters("sync", self.data_s3local)
        assert missing_dir.exists()


class TestParametersDataModel:
    """Test ParametersDataModel."""

    @pytest.mark.parametrize(
        "dest, src, expected",
        [
            ("test-dest", "test-src", "locallocal"),
            ("test-dest", "s3://test-src", "s3local"),
            ("s3://test-dest", "test-src", "locals3"),
            ("s3://test-dest", "s3://test-src", "s3s3"),
        ],
    )
    def test_determine_paths_type(self, dest: str, expected: PathsType, src: str) -> None:
        """Test _determine_paths_type."""
        assert ParametersDataModel(dest=dest, src=src).paths_type == expected

    def test_field_defaults(self) -> None:
        """Test field defaults."""
        kwargs = {"dest": "test-dest", "src": "test-src"}
        obj = ParametersDataModel(**kwargs)
        assert obj.dest == kwargs["dest"]
        assert obj.src == kwargs["src"]
        assert not obj.delete
        assert not obj.dir_op
        assert not obj.exact_timestamps
        assert not obj.follow_symlinks
        assert not obj.is_move
        assert not obj.only_show_errors
        assert not obj.page_size
        assert obj.paths_type == "locallocal"
        assert not obj.size_only

    @pytest.mark.parametrize(
        "provided, expected",
        [
            ("s3://test-bucket", "s3://test-bucket/"),
            ("s3://test-bucket/", "s3://test-bucket/"),
            ("s3://test-bucket/key.txt", "s3://test-bucket/key.txt"),
            ("./local", "./local"),
            ("./local/", "./local/"),
            ("./local/test.txt", "./local/test.txt"),
        ],
    )
    def test_normalize_s3_trailing_slash(self, provided: str, expected: str) -> None:
        """Test _normalize_s3_trailing_slash."""
        assert ParametersDataModel(dest=provided, src="test").dest == expected
        assert ParametersDataModel(dest="test", src=provided).src == expected

    @pytest.mark.parametrize(
        "kwargs, error_locs",
        [({"dest": "test-dest"}, ["src"]), ({"src": "test-src"}, ["dest"])],
    )
    def test_required_fields(self, error_locs: List[str], kwargs: Dict[str, Any]) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            ParametersDataModel(**kwargs)
        errors = excinfo.value.errors()
        for index, loc in enumerate(error_locs):
            assert errors[index]["loc"] == (loc,)
