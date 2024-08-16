"""Test runway.env_mgr.tfenv."""

# pyright: reportFunctionMemberAccess=none
from __future__ import annotations

import json
import re
import subprocess
from typing import TYPE_CHECKING, Any, Optional
from unittest.mock import MagicMock, call

import hcl
import hcl2
import pytest

from runway._logging import LogLevels
from runway.env_mgr.tfenv import (
    TF_VERSION_FILENAME,
    TFEnvManager,
    get_available_tf_versions,
    get_latest_tf_version,
    load_terraform_module,
)
from runway.exceptions import HclParserError
from runway.utils import Version

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    from pytest_mock import MockerFixture
    from pytest_subprocess import FakeProcess

MODULE = "runway.env_mgr.tfenv"

HCL_BACKEND_REMOTE = """
terraform {
  backend "remote" {
    organization = "test"
    workspaces {
      prefix = "test-"
    }
  }
}
"""
HCL_BACKEND_S3 = """
terraform {
  backend "s3" {
    bucket = "name"
  }
}
"""
HCL_ATTR_LIST = """
terraform {
  some_attr = [
    "val1",
    "val2"
  ]
}
"""


def test_get_available_tf_versions(mocker: MockerFixture) -> None:
    """Test runway.env_mgr.tfenv.get_available_tf_versions."""
    mock_requests = mocker.patch(f"{MODULE}.requests")
    response: dict[str, Any] = {"terraform": {"versions": {"0.12.0": {}, "0.12.0-beta": {}}}}
    mock_requests.get.return_value = MagicMock(text=json.dumps(response))
    assert get_available_tf_versions() == ["0.12.0"]
    assert get_available_tf_versions(include_prerelease=True) == [
        "0.12.0",
        "0.12.0-beta",
    ]


def test_get_latest_tf_version(mocker: MockerFixture) -> None:
    """Test runway.env_mgr.tfenv.get_latest_tf_version."""
    mock_get_available_tf_versions = mocker.patch(
        f"{MODULE}.get_available_tf_versions", return_value=["latest"]
    )
    assert get_latest_tf_version() == "latest"
    mock_get_available_tf_versions.assert_called_once_with(False)
    assert get_latest_tf_version(include_prerelease=True) == "latest"
    mock_get_available_tf_versions.assert_called_with(True)


@pytest.mark.parametrize(
    "parser, expected",
    [
        (hcl, {"terraform": {"backend": {"s3": {"bucket": "name"}}}}),
        (hcl2, {"terraform": [{"backend": [{"s3": {"bucket": "name"}}]}]}),
    ],
)
def test_load_terraform_module(
    parser: ModuleType, expected: dict[str, Any], tmp_path: Path
) -> None:
    """Test runway.env_mgr.tfenv.load_terraform_module."""
    tf_file = tmp_path / "module.tf"
    tf_file.write_text(HCL_BACKEND_S3)

    assert load_terraform_module(parser, tmp_path) == expected


def test_load_terraform_module_raise_hcl_parser_error(tmp_path: Path) -> None:
    """Test load_terraform_module raise HclParserError."""
    tf_file = tmp_path / "module.tf"
    tf_file.write_text(HCL_BACKEND_S3)

    mock_parser = MagicMock(loads=MagicMock(side_effect=Exception))
    mock_parser.__name__ = "TestParser"

    with pytest.raises(HclParserError) as excinfo:
        load_terraform_module(mock_parser, tmp_path)

    assert excinfo.value.file_path == tf_file
    assert str(tf_file) in excinfo.value.message
    assert "TestParser".upper() in excinfo.value.message


class TestTFEnvManager:
    """Test runway.env_mgr.tfenv.TFEnvManager."""

    @pytest.mark.parametrize(
        "response, expected",
        [
            ({}, {"type": None, "config": {}}),
            (hcl.loads(HCL_BACKEND_S3), {"type": "s3", "config": {"bucket": "name"}}),
            (hcl2.loads(HCL_BACKEND_S3), {"type": "s3", "config": {"bucket": "name"}}),
            (
                hcl.loads(HCL_BACKEND_REMOTE),
                {
                    "type": "remote",
                    "config": {
                        "organization": "test",
                        "workspaces": {"prefix": "test-"},
                    },
                },
            ),
            (
                hcl2.loads(HCL_BACKEND_REMOTE),
                {
                    "type": "remote",
                    "config": {
                        "organization": "test",
                        "workspaces": {"prefix": "test-"},
                    },
                },
            ),
        ],
    )
    def test_backend(
        self,
        mocker: MockerFixture,
        response: dict[str, Any],
        expected: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test backend."""
        mocker.patch(f"{MODULE}.load_terraform_module", return_value=response)
        tfenv = TFEnvManager(tmp_path)
        assert tfenv.backend == expected

    def test_get_min_required(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test get_min_required."""
        mocker.patch.object(TFEnvManager, "terraform_block", {})
        tfenv = TFEnvManager(tmp_path)

        with pytest.raises(SystemExit) as excinfo:
            assert tfenv.get_min_required()
        assert excinfo.value.code

        mocker.patch.object(tfenv, "terraform_block", {"required_version": "!=0.12.0"})
        with pytest.raises(SystemExit) as excinfo:
            assert tfenv.get_min_required()
        assert excinfo.value.code

        mocker.patch.object(tfenv, "terraform_block", {"required_version": "~>0.12.0"})
        assert tfenv.get_min_required() == "0.12.0"

    @pytest.mark.parametrize(
        "output, expected",
        [
            ("", None),
            ("Terraform v0.15.5\non darwin_amd64", Version("v0.15.5")),
            (
                "Terraform v0.10.3\n\n"
                "Your version of Terraform is out of date! The latest version\n"
                "is 0.15.5. You can update by downloading from www.terraform.io",
                Version("v0.10.3"),
            ),
            ("Terraform v0.15.0-alpha.13", Version("v0.15.0-alpha.13")),
        ],
    )
    def test_get_version_from_executable(
        self,
        expected: Optional[Version],
        fake_process: FakeProcess,
        output: str,
    ) -> None:
        """Test get_version_from_executable."""
        fake_process.register_subprocess(["usr/tfenv/terraform", "-version"], stdout=output)
        assert TFEnvManager.get_version_from_executable("usr/tfenv/terraform") == expected

    def test_get_version_from_executable_raise(self, fake_process: FakeProcess) -> None:
        """Test get_version_from_executable raise exception."""
        fake_process.register_subprocess(["usr/tfenv/terraform", "-version"], returncode=1)
        with pytest.raises(subprocess.CalledProcessError, match="returned non-zero exit status 1"):
            TFEnvManager.get_version_from_executable("usr/tfenv/terraform")

    def test_get_version_from_file(self, tmp_path: Path) -> None:
        """Test get_version_from_file."""
        tfenv = TFEnvManager(tmp_path)

        # no version file or path
        assert not tfenv.get_version_from_file()
        del tfenv.version_file

        # path provided
        version_file = tmp_path / ".version"
        version_file.write_text("0.11.5")
        assert tfenv.get_version_from_file(version_file) == "0.11.5"

        # path not provided; use version file
        version_file = tmp_path / TF_VERSION_FILENAME
        version_file.write_text("0.12.0")
        assert tfenv.get_version_from_file(version_file) == "0.12.0"

    def test_install(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test install."""
        version = Version("0.15.5")
        mocker.patch.object(TFEnvManager, "version", version)
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        mock_download = mocker.patch(f"{MODULE}.download_tf_release")
        tfenv = TFEnvManager(tmp_path)
        (tfenv.versions_dir / "0.15.2").mkdir()
        assert tfenv.install() == str(tfenv.bin)
        mock_download.assert_called_once_with(
            str(version), tfenv.versions_dir, tfenv.command_suffix
        )

    def test_install_already_installed(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test install."""
        version = Version("0.15.5")
        mocker.patch.object(TFEnvManager, "version", version)
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        mock_download = mocker.patch(f"{MODULE}.download_tf_release")
        tfenv = TFEnvManager(tmp_path)
        (tfenv.versions_dir / str(version)).mkdir()
        assert tfenv.install() == str(tfenv.bin)
        mock_download.assert_not_called()

    def test_install_set_version(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test install set version."""
        version = Version("0.15.5")
        mocker.patch.object(TFEnvManager, "version", version)
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        mock_download = mocker.patch(f"{MODULE}.download_tf_release")
        mock_set_version = mocker.patch.object(TFEnvManager, "set_version", return_value=None)
        tfenv = TFEnvManager(tmp_path)
        assert tfenv.install(str(version))
        mock_download.assert_called_once_with(
            str(version), tfenv.versions_dir, tfenv.command_suffix
        )
        mock_set_version.assert_called_once_with(str(version))

    def test_install_version_undefined(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test install."""
        mocker.patch.object(TFEnvManager, "version", None)
        tfenv = TFEnvManager(tmp_path)
        with pytest.raises(ValueError, match=r"^version not provided and unable to find .*"):
            tfenv.install()

    def test_list_installed(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test list_installed."""
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        version_dirs = [tmp_path / "0.13.0", tmp_path / "1.0.0"]
        for v_dir in version_dirs:
            v_dir.mkdir()
        (tmp_path / "something.txt").touch()
        result = list(TFEnvManager().list_installed())  # convert generator to list
        result.sort()  # sort list for comparison
        assert result == version_dirs

    def test_list_installed_none(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test list_installed."""
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        assert not list(TFEnvManager().list_installed())

    @pytest.mark.parametrize(
        "provided, expected",
        [
            ("0.15.2", Version("0.15.2")),
            ("0.15.0-alpha13", Version("0.15.0-alpha13")),
        ],
    )
    def test_parse_version_string(self, provided: str, expected: Optional[Version]) -> None:
        """Test parse_version_string."""
        assert TFEnvManager.parse_version_string(provided) == expected

    def test_parse_version_string_raise_value_error(self) -> None:
        """Test parse_version_string."""
        with pytest.raises(
            ValueError,
            match=re.escape(
                f"provided version doesn't conform to regex: {TFEnvManager.VERSION_REGEX}"
            ),
        ):
            TFEnvManager.parse_version_string("0.15")

    def test_set_version(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test set_version."""
        version = Version("0.15.5")
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        mocker.patch.object(TFEnvManager, "get_version_from_file", return_value=None)
        tfenv = TFEnvManager(tmp_path)
        (tfenv.versions_dir / str(version)).mkdir()
        assert not tfenv.current_version
        assert not tfenv.set_version(str(version))
        assert tfenv.version == version
        assert tfenv.current_version == str(version)

    def test_set_version_same(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test set_version same."""
        version = mocker.patch.object(TFEnvManager, "version")
        tfenv = TFEnvManager(tmp_path)
        tfenv.current_version = "0.15.5"
        assert not tfenv.set_version("0.15.5")
        assert tfenv.current_version == "0.15.5"
        assert tfenv.version == version

    @pytest.mark.parametrize(
        "response, expected",
        [  # type: ignore
            ([{}], {}),
            ([hcl2.loads(HCL_BACKEND_S3)], {"backend": {"s3": {"bucket": "name"}}}),
            (
                [
                    HclParserError(Exception("something"), "/test.tf"),
                    hcl.loads(HCL_BACKEND_S3),
                ],
                {"backend": {"s3": {"bucket": "name"}}},
            ),
            (
                [hcl2.loads(HCL_BACKEND_REMOTE)],
                {
                    "backend": {
                        "remote": {
                            "organization": "test",
                            "workspaces": {"prefix": "test-"},
                        }
                    }
                },
            ),
            (
                [
                    HclParserError(Exception("something"), "/test.tf"),
                    hcl.loads(HCL_BACKEND_REMOTE),
                ],
                {
                    "backend": {
                        "remote": {
                            "organization": "test",
                            "workspaces": {"prefix": "test-"},
                        }
                    }
                },
            ),
            ([hcl2.loads(HCL_ATTR_LIST)], {"some_attr": ["val1", "val2"]}),
            (
                [
                    HclParserError(Exception("something"), "/test.tf"),
                    hcl.loads(HCL_ATTR_LIST),
                ],
                {"some_attr": ["val1", "val2"]},
            ),
            (
                [
                    HclParserError(Exception("something"), "/test.tf"),
                    HclParserError(Exception("something"), "/test.tf"),
                ],
                {},
            ),
        ],
    )
    def test_terraform_block(
        self,
        caplog: pytest.LogCaptureFixture,
        expected: dict[str, Any],
        mocker: MockerFixture,
        response: list[Any],
        tmp_path: Path,
    ) -> None:
        """Test terraform_block."""
        caplog.set_level(LogLevels.VERBOSE, logger=MODULE)
        mock_load_terraform_module = mocker.patch(
            f"{MODULE}.load_terraform_module", side_effect=response
        )
        tfenv = TFEnvManager(tmp_path)

        assert tfenv.terraform_block == expected

        if not isinstance(response[0], dict):
            assert "failed to parse as HCL2; trying HCL" in "\n".join(caplog.messages)
            mock_load_terraform_module.assert_has_calls(
                [call(hcl2, tmp_path), call(hcl, tmp_path)]  # type: ignore
            )
        else:
            mock_load_terraform_module.assert_called_once_with(hcl2, tmp_path)

    def test_version(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test version."""
        version = Version("0.15.5")
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        mock_get_available_tf_versions = mocker.patch(
            f"{MODULE}.get_available_tf_versions", return_value=[]
        )
        mock_get_version_from_file = mocker.patch.object(
            TFEnvManager, "get_version_from_file", return_value=None
        )
        tfenv = TFEnvManager(tmp_path)
        (tfenv.versions_dir / str(version)).mkdir()
        tfenv.current_version = str(version)
        assert tfenv.version == version
        assert tfenv.current_version == str(version)
        mock_get_version_from_file.assert_not_called()
        mock_get_available_tf_versions.assert_not_called()

    def test_version_latest(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test version latest."""
        version = Version("0.15.5")
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        mock_get_available_tf_versions = mocker.patch(
            f"{MODULE}.get_available_tf_versions", return_value=["0.15.5", "0.15.4"]
        )
        mock_get_version_from_file = mocker.patch.object(
            TFEnvManager, "get_version_from_file", return_value="latest"
        )
        tfenv = TFEnvManager(tmp_path)
        assert tfenv.version == version
        assert tfenv.current_version == str(version)
        mock_get_version_from_file.assert_called_once_with()
        mock_get_available_tf_versions.assert_called_once_with(False)

    def test_version_latest_partial(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test version latest."""
        version = Version("0.14.3")
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        mock_get_available_tf_versions = mocker.patch(
            f"{MODULE}.get_available_tf_versions",
            return_value=["0.15.5", "0.15.4", "0.14.3", "0.14.2", "0.13.8"],
        )
        mock_get_version_from_file = mocker.patch.object(
            TFEnvManager, "get_version_from_file", return_value="latest:0.14"
        )
        tfenv = TFEnvManager(tmp_path)
        assert tfenv.version == version
        assert tfenv.current_version == str(version)
        mock_get_version_from_file.assert_called_once_with()
        mock_get_available_tf_versions.assert_called_once_with(False)

    def test_version_min_required(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test version minimum required."""
        version = Version("0.14.3")
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        mock_get_available_tf_versions = mocker.patch(
            f"{MODULE}.get_available_tf_versions",
            return_value=["0.15.5", "0.15.4", "0.14.3", "0.14.2", "0.13.8"],
        )
        mock_get_min_required = mocker.patch.object(
            TFEnvManager, "get_min_required", return_value="0.14.3"
        )
        mock_get_version_from_file = mocker.patch.object(
            TFEnvManager, "get_version_from_file", return_value="min-required"
        )
        tfenv = TFEnvManager(tmp_path)
        assert tfenv.version == version
        assert tfenv.current_version == str(version)
        mock_get_version_from_file.assert_called_once_with()
        mock_get_min_required.assert_called_once_with()
        mock_get_available_tf_versions.assert_called_once_with(True)

    def test_version_unavailable(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test version latest."""
        mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
        mocker.patch(
            f"{MODULE}.get_available_tf_versions",
            return_value=["0.15.5", "0.15.4", "0.14.3", "0.14.2", "0.13.8"],
        )
        tfenv = TFEnvManager(tmp_path)
        tfenv.current_version = "1.0.0"
        with pytest.raises(SystemExit):
            assert not tfenv.version

    def test_version_undefined(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test version not specified."""
        mock_get_version_from_file = mocker.patch.object(
            TFEnvManager, "get_version_from_file", return_value=None
        )
        tfenv = TFEnvManager(tmp_path)
        assert tfenv.version is None
        assert tfenv.current_version is None
        mock_get_version_from_file.assert_called_once_with()

    def test_version_file(self, tmp_path: Path) -> None:
        """Test version_file."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        tfenv = TFEnvManager(subdir)

        # no version file
        assert not tfenv.version_file
        del tfenv.version_file

        # version file in parent dir
        expected = tmp_path / TF_VERSION_FILENAME
        expected.touch()
        assert tfenv.version_file == expected
        del tfenv.version_file

        # version file in module dir
        expected = subdir / TF_VERSION_FILENAME
        expected.touch()
        assert tfenv.version_file == expected
