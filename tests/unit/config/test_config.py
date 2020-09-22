"""Test runway.config."""
# pylint: disable=no-self-use
from pathlib import Path

import pytest
import yaml
from _pytest.monkeypatch import MonkeyPatch
from mock import MagicMock, patch

from runway.cfngin.exceptions import MissingEnvironment
from runway.config import CfnginConfig
from runway.config.models.cfngin import (
    CfnginConfigDefinitionModel,
    CfnginPackageSourcesDefinitionModel,
)

MODULE = "runway.config"


class TestCfnginConfig:
    """Test runway.config.CfnginConfig."""

    def test_dump(self) -> None:
        """Test dump."""
        config = CfnginConfigDefinitionModel(namespace="test")
        obj = CfnginConfig(config)
        assert obj.dump() == yaml.dump(
            config.dict(exclude_unset=True), default_flow_style=False
        )

    def test_find_config_file(self, tmp_path: Path) -> None:
        """Test find_config_file."""
        test_01 = tmp_path / "01-config.yaml"
        test_01.touch()
        test_02 = tmp_path / "02-config.yml"
        test_02.touch()
        test_03 = tmp_path / "03-config.yaml"
        test_03.touch()
        (tmp_path / "no-match").touch()
        (tmp_path / "buildspec.yml").touch()
        (tmp_path / "docker-compose.yml").touch()
        (tmp_path / "runway.yml").touch()
        (tmp_path / "runway.yaml").touch()
        (tmp_path / "runway.module.yml").touch()
        (tmp_path / "runway.module.yaml").touch()
        assert CfnginConfig.find_config_file(tmp_path) == [test_01, test_02, test_03]

    def test_find_config_file_file(self, tmp_path: Path) -> None:
        """Test find_config_file with file provided as path."""
        test = tmp_path / "config.yml"
        test.touch()
        assert CfnginConfig.find_config_file(test) == [test]

    def test_find_config_file_no_path(self, cd_tmp_path: Path) -> None:
        """Test find_config_file without providing a path."""
        test = cd_tmp_path / "config.yml"
        test.touch()
        assert CfnginConfig.find_config_file() == [test]

    @patch(MODULE + ".register_lookup_handler")
    @patch(MODULE + ".sys")
    def test_load(
        self,
        mock_sys: MagicMock,
        mock_register_lookup_handler: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test load."""
        config = CfnginConfig(CfnginConfigDefinitionModel(namespace="test"))

        config.load()
        mock_sys.path.append.assert_not_called()
        mock_register_lookup_handler.assert_not_called()

        config.sys_path = tmp_path
        config.load()
        mock_sys.path.append.assert_called_once_with(str(config.sys_path))
        mock_register_lookup_handler.assert_not_called()

        config.lookups = {"custom-lookup": "path"}
        config.load()
        mock_register_lookup_handler.assert_called_once_with("custom-lookup", "path")

    def test_parse_file(self, tmp_path: Path) -> None:
        """Test parse_file."""
        config_yml = tmp_path / "config.yml"
        data = {"namespace": "test"}
        config_yml.write_text(yaml.dump(data))
        config = CfnginConfig.parse_file(file_path=config_yml)
        assert config.namespace == data["namespace"]

    def test_parse_obj(self) -> None:
        """Test parse_obj.

        This test primarily focuses on the conversion of dicts to lists.

        """
        data = {
            "namespace": "test",
            "post_build": {"test-hook": {"path": "./"}},
            "post_destroy": {"test-hook": {"path": "./"}},
            "pre_build": {"test-hook": {"path": "./"}},
            "pre_destroy": {"test-hook": {"path": "./"}},
            "stacks": {"test-stack": {"template_path": "./"}},
        }
        expected = {
            "namespace": "test",
            "post_build": [{"path": "./"}],
            "post_destroy": [{"path": "./"}],
            "pre_build": [{"path": "./"}],
            "pre_destroy": [{"path": "./"}],
            "stacks": [{"name": "test-stack", "template_path": Path.cwd().resolve()}],
        }
        assert CfnginConfig.parse_obj(data).dump() == yaml.dump(expected)

    def test_parse_raw(self, monkeypatch: MonkeyPatch) -> None:
        """Test parse_raw."""
        mock_render_raw_data = MagicMock()
        mock_parse_obj = MagicMock()
        mock_process_package_sources = MagicMock()
        monkeypatch.setattr(CfnginConfig, "render_raw_data", mock_render_raw_data)
        monkeypatch.setattr(CfnginConfig, "parse_obj", mock_parse_obj)
        monkeypatch.setattr(
            CfnginConfig, "process_package_sources", mock_process_package_sources
        )

        data = {"namespace": "test"}
        data_str = yaml.dump(data)
        mock_render_raw_data.return_value = data_str
        mock_parse_obj.return_value = data
        mock_process_package_sources.return_value = data_str

        assert CfnginConfig.parse_raw(data_str, skip_package_sources=True) == data
        mock_render_raw_data.assert_called_once_with(yaml.dump(data), parameters={})
        mock_parse_obj.assert_called_once_with(data)
        mock_process_package_sources.assert_not_called()

        assert CfnginConfig.parse_raw(data_str, parameters={"key": "val"}) == data
        mock_render_raw_data.assert_called_with(
            yaml.dump(data), parameters={"key": "val"}
        )
        mock_process_package_sources.assert_called_once_with(
            data_str, parameters={"key": "val"}
        )
        assert mock_parse_obj.call_count == 2

    @patch(MODULE + ".SourceProcessor")
    def test_process_package_sources(
        self, mock_source_processor: MagicMock, monkeypatch: MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test process_package_sources."""
        mock_render_raw_data = MagicMock(return_value="rendered")
        monkeypatch.setattr(CfnginConfig, "render_raw_data", mock_render_raw_data)
        mock_source_processor.return_value = mock_source_processor
        mock_source_processor.configs_to_merge = []

        raw_data = "namespace: test"
        merge_data = "merged: value"
        other_config = tmp_path / "other_config.yml"
        other_config.write_text(merge_data)
        assert (
            CfnginConfig.process_package_sources(raw_data, parameters={"key": "val"})
            == raw_data
        )
        mock_source_processor.assert_called_once_with(
            sources=CfnginPackageSourcesDefinitionModel(), cache_dir=None
        )
        mock_source_processor.get_package_sources.assert_called_once_with()
        mock_render_raw_data.assert_not_called()

        data = {"namespace": "test", "package_sources": {"git": [{"uri": "something"}]}}
        raw_data = yaml.dump(data)
        mock_source_processor.configs_to_merge = [str(other_config.resolve())]
        assert (
            CfnginConfig.process_package_sources(raw_data, parameters={"key": "val"})
            == "rendered"
        )
        mock_source_processor.assert_called_with(
            sources=CfnginPackageSourcesDefinitionModel(git=[{"uri": "something"}]),
            cache_dir=None,
        )
        assert mock_source_processor.call_count == 2
        expected = data.copy()
        expected["merged"] = "value"
        mock_render_raw_data.assert_called_once_with(
            yaml.dump(expected), parameters={"key": "val"}
        )

    def test_render_raw_data(self) -> None:
        """Test render_raw_data."""
        raw_data = "namespace: ${namespace}"
        expected = "namespace: test"
        assert (
            CfnginConfig.render_raw_data(raw_data, parameters={"namespace": "test"})
            == expected
        )

    def test_render_raw_data_missing_value(self) -> None:
        """Test render_raw_data missing value."""
        with pytest.raises(MissingEnvironment) as excinfo:
            CfnginConfig.render_raw_data("namespace: ${namespace}")
        assert excinfo.value.key == "namespace"

    def test_render_raw_data_ignore_lookup(self) -> None:
        """Test render_raw_data ignores lookups."""
        lookup_raw_data = "namespace: ${env something}"
        assert CfnginConfig.render_raw_data(lookup_raw_data) == lookup_raw_data
