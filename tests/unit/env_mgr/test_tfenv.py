"""Test runway.env_mgr.tfenv."""
# pylint: disable=no-self-use
import json
import sys

import hcl
import pytest
import six
from mock import MagicMock, call, patch

from runway._logging import LogLevels
from runway.env_mgr.tfenv import (
    TF_VERSION_FILENAME,
    TFEnvManager,
    get_available_tf_versions,
    get_latest_tf_version,
    load_terrafrom_module,
)

# TODO remove condition and import-error when dropping python 2
if sys.version_info >= (3, 6):
    import hcl2  # pylint: disable=import-error
else:
    hcl2 = hcl  # pylint: disable=invalid-name

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


@patch(MODULE + ".requests")
def test_get_available_tf_versions(mock_requests):
    """Test runway.env_mgr.tfenv.get_available_tf_versions."""
    response = {"terraform": {"versions": {"0.12.0": {}, "0.12.0-beta": {}}}}
    mock_requests.get.return_value = MagicMock(text=json.dumps(response))
    assert get_available_tf_versions() == ["0.12.0"]
    assert get_available_tf_versions(include_prerelease=True) == [
        "0.12.0-beta",
        "0.12.0",
    ]


@patch(MODULE + ".get_available_tf_versions")
def test_get_latest_tf_version(mock_get_available_tf_versions):
    """Test runway.env_mgr.tfenv.get_latest_tf_version."""
    mock_get_available_tf_versions.return_value = ["latest"]
    assert get_latest_tf_version() == "latest"
    mock_get_available_tf_versions.assert_called_once_with(False)
    assert get_latest_tf_version(include_prerelease=True) == "latest"
    mock_get_available_tf_versions.assert_called_with(True)


@pytest.mark.skipif(sys.version_info < (3, 6), reason="dependency requires >=3.6")
@pytest.mark.parametrize(
    "parser, expected",
    [
        (hcl, {"terraform": {"backend": {"s3": {"bucket": "name"}}}}),
        (hcl2, {"terraform": [{"backend": [{"s3": {"bucket": ["name"]}}]}]}),
    ],
)
def test_load_terrafrom_module(parser, expected, tmp_path):
    """Test runway.env_mgr.tfenv.load_terrafrom_module."""
    tf_file = tmp_path / "module.tf"
    tf_file.write_text(six.u(HCL_BACKEND_S3))

    assert load_terrafrom_module(parser, tmp_path) == expected


class TestTFEnvManager(object):
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
    @patch(MODULE + ".load_terrafrom_module")
    def test_backend(self, mock_load_terrafrom_module, response, expected, tmp_path):
        """Test backend."""
        mock_load_terrafrom_module.return_value = response
        tfenv = TFEnvManager(tmp_path)
        assert tfenv.backend == expected

    def test_get_min_required(self, monkeypatch, tmp_path):
        """Test get_min_required."""
        monkeypatch.setattr(TFEnvManager, "terraform_block", {})
        tfenv = TFEnvManager(tmp_path)

        with pytest.raises(SystemExit) as excinfo:
            assert tfenv.get_min_required()
        assert excinfo.value.code

        monkeypatch.setattr(tfenv, "terraform_block", {"required_version": "!=0.12.0"})
        with pytest.raises(SystemExit) as excinfo:
            assert tfenv.get_min_required()
        assert excinfo.value.code

        monkeypatch.setattr(tfenv, "terraform_block", {"required_version": "~>0.12.0"})
        assert tfenv.get_min_required() == "0.12.0"

    def test_get_version_from_file(self, tmp_path):
        """Test get_version_from_file."""
        tfenv = TFEnvManager(tmp_path)

        # no version file or path
        assert not tfenv.get_version_from_file()
        del tfenv.version_file

        # path provided
        version_file = tmp_path / ".version"
        version_file.write_text(six.u("0.11.5"))
        assert tfenv.get_version_from_file(version_file) == "0.11.5"

        # path not provided; use version file
        version_file = tmp_path / TF_VERSION_FILENAME
        version_file.write_text(six.u("0.12.0"))
        assert tfenv.get_version_from_file(version_file) == "0.12.0"

    @patch(MODULE + ".get_available_tf_versions")
    @patch(MODULE + ".download_tf_release")
    def test_install(
        self, mock_download, mock_available_versions, monkeypatch, tmp_path
    ):
        """Test install."""
        mock_available_versions.return_value = ["0.12.0", "0.11.5"]
        monkeypatch.setattr(TFEnvManager, "versions_dir", tmp_path)
        monkeypatch.setattr(
            TFEnvManager, "get_version_from_file", MagicMock(return_value="0.11.5")
        )
        tfenv = TFEnvManager(tmp_path)

        assert tfenv.install("0.12.0")
        mock_available_versions.assert_called_once_with(True)
        mock_download.assert_called_once_with(
            "0.12.0", tfenv.versions_dir, tfenv.command_suffix
        )
        assert tfenv.current_version == "0.12.0"

        assert tfenv.install()
        mock_download.assert_called_with(
            "0.11.5", tfenv.versions_dir, tfenv.command_suffix
        )
        assert tfenv.current_version == "0.11.5"

    @patch(MODULE + ".get_available_tf_versions")
    @patch(MODULE + ".download_tf_release")
    def test_install_already_installed(
        self, mock_download, mock_available_versions, monkeypatch, tmp_path
    ):
        """Test install with version already installed."""
        mock_available_versions.return_value = ["0.12.0"]
        monkeypatch.setattr(TFEnvManager, "versions_dir", tmp_path)
        tfenv = TFEnvManager(tmp_path)
        (tfenv.versions_dir / "0.12.0").mkdir()

        assert tfenv.install("0.12.0")
        mock_available_versions.assert_not_called()
        mock_download.assert_not_called()
        assert tfenv.current_version == "0.12.0"

        assert tfenv.install(r"0\.12\..*")  # regex does not match dir

    @patch(MODULE + ".get_available_tf_versions")
    @patch(MODULE + ".download_tf_release")
    def test_install_latest(
        self, mock_download, mock_available_versions, monkeypatch, tmp_path
    ):
        """Test install latest."""
        mock_available_versions.return_value = ["0.12.0", "0.11.5"]
        monkeypatch.setattr(TFEnvManager, "versions_dir", tmp_path)
        tfenv = TFEnvManager(tmp_path)

        assert tfenv.install("latest")
        mock_available_versions.assert_called_once_with(False)
        mock_download.assert_called_once_with(
            "0.12.0", tfenv.versions_dir, tfenv.command_suffix
        )
        assert tfenv.current_version == "0.12.0"

        assert tfenv.install("latest:0.11.5")
        mock_available_versions.assert_called_with(False)
        mock_download.assert_called_with(
            "0.11.5", tfenv.versions_dir, tfenv.command_suffix
        )
        assert tfenv.current_version == "0.11.5"

    @patch(MODULE + ".get_available_tf_versions")
    @patch(MODULE + ".download_tf_release")
    def test_install_min_required(
        self, mock_download, mock_available_versions, monkeypatch, tmp_path
    ):
        """Test install min_required."""
        mock_available_versions.return_value = ["0.12.0"]
        monkeypatch.setattr(TFEnvManager, "versions_dir", tmp_path)
        monkeypatch.setattr(
            TFEnvManager, "get_min_required", MagicMock(return_value="0.12.0")
        )
        tfenv = TFEnvManager(tmp_path)

        assert tfenv.install("min-required")
        mock_available_versions.assert_called_once_with(True)
        mock_download.assert_called_once_with(
            "0.12.0", tfenv.versions_dir, tfenv.command_suffix
        )
        assert tfenv.current_version == "0.12.0"
        tfenv.get_min_required.assert_called_once_with()  # pylint: disable=no-member

    def test_install_no_version(self, tmp_path):
        """Test install with no version available."""
        tfenv = TFEnvManager(tmp_path)

        with pytest.raises(ValueError) as excinfo:
            assert tfenv.install()
        assert str(excinfo.value) == (
            "version not provided and unable to find a .terraform-version file"
        )

    @patch(MODULE + ".get_available_tf_versions")
    @patch(MODULE + ".download_tf_release")
    def test_install_unavailable(
        self, mock_download, mock_available_versions, monkeypatch, tmp_path
    ):
        """Test install."""
        mock_available_versions.return_value = []
        monkeypatch.setattr(TFEnvManager, "versions_dir", tmp_path)
        tfenv = TFEnvManager(tmp_path)

        with pytest.raises(SystemExit) as excinfo:
            assert tfenv.install("0.12.0")
        assert excinfo.value.code == 1
        mock_available_versions.assert_called_once_with(True)
        mock_download.assert_not_called()
        assert not tfenv.current_version

    @pytest.mark.skipif(sys.version_info < (3, 6), reason="dependency requires >=3.6")
    @pytest.mark.parametrize(
        "response, expected",
        [
            ([{}], {}),
            ([hcl2.loads(HCL_BACKEND_S3)], {"backend": {"s3": {"bucket": "name"}}}),
            (
                [Exception, hcl.loads(HCL_BACKEND_S3)],
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
                [Exception, hcl.loads(HCL_BACKEND_REMOTE)],
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
            ([Exception, hcl.loads(HCL_ATTR_LIST)], {"some_attr": ["val1", "val2"]}),
        ],
    )
    @patch(MODULE + ".load_terrafrom_module")
    def test_terraform_block(
        self, mock_load_terrafrom_module, response, expected, caplog, tmp_path
    ):
        """Test terraform_block."""
        caplog.set_level(LogLevels.VERBOSE, logger=MODULE)
        mock_load_terrafrom_module.side_effect = response
        tfenv = TFEnvManager(tmp_path)

        assert tfenv.terraform_block == expected

        if not isinstance(response[0], dict):
            assert "failed to parse as HCL2; trying HCL" in "\n".join(caplog.messages)
            mock_load_terrafrom_module.assert_has_calls(
                [call(hcl2, tmp_path), call(hcl, tmp_path)]
            )
        else:
            mock_load_terrafrom_module.assert_called_once_with(hcl2, tmp_path)

    def test_version_file(self, tmp_path):
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
