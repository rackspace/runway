"""Test runway.config."""

# pyright: basic
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import yaml
from pydantic import BaseModel

from runway.cfngin.exceptions import MissingEnvironment
from runway.config import BaseConfig, CfnginConfig, RunwayConfig
from runway.config.models.cfngin import (
    CfnginConfigDefinitionModel,
    CfnginPackageSourcesDefinitionModel,
)
from runway.exceptions import ConfigNotFound

if TYPE_CHECKING:
    from pathlib import Path


MODULE = "runway.config"


class ExampleModel(BaseModel):
    """Basic model used for testing."""

    name: str = "test"


class TestBaseConfig:
    """Test runway.config.BaseConfig."""

    def test_dump(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test dump."""
        mock_dict = MagicMock(return_value={"name": "test"})
        monkeypatch.setattr(ExampleModel, "dict", mock_dict)
        obj = BaseConfig(ExampleModel())
        assert obj.dump() == "name: test\n"
        mock_dict.assert_called_once_with(
            by_alias=False,
            exclude=None,
            exclude_defaults=False,
            exclude_none=False,
            exclude_unset=True,
            include=None,
        )


class TestCfnginConfig:
    """Test runway.config.CfnginConfig."""

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

    def test_parse_file_file_path(self, tmp_path: Path) -> None:
        """Test parse_file with file_path."""
        config_yml = tmp_path / "config.yml"
        data = {"namespace": "test"}
        config_yml.write_text(yaml.dump(data))
        config = CfnginConfig.parse_file(file_path=config_yml)
        assert config.namespace == data["namespace"]

    def test_parse_file_file_path_missing(self, tmp_path: Path) -> None:
        """Test parse_file with file_path missing."""
        config_yml = tmp_path / "config.yml"
        with pytest.raises(ConfigNotFound) as excinfo:
            CfnginConfig.parse_file(file_path=config_yml)
        assert excinfo.value.path == config_yml

    def test_parse_file_find_config_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test parse_file with path."""
        file_path = tmp_path / "test.yml"
        file_path.write_text("name: test\n")
        mock_find_config_file = MagicMock(return_value=[file_path])
        mock_parse_raw = MagicMock(return_value=None)
        monkeypatch.setattr(CfnginConfig, "find_config_file", mock_find_config_file)
        monkeypatch.setattr(CfnginConfig, "parse_raw", mock_parse_raw)
        assert not CfnginConfig.parse_file(path=tmp_path, work_dir=tmp_path)
        mock_find_config_file.assert_called_once_with(tmp_path)
        mock_parse_raw.assert_called_once_with(
            file_path.read_text(), path=file_path, parameters={}, work_dir=tmp_path
        )

    def test_parse_file_find_config_file_value_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test parse_file with path raise ValueError."""
        mock_find_config_file = MagicMock(return_value=[tmp_path / "01.yml", tmp_path / "02.yml"])
        monkeypatch.setattr(CfnginConfig, "find_config_file", mock_find_config_file)
        with pytest.raises(ValueError, match="more than one"):
            CfnginConfig.parse_file(path=tmp_path)

    def test_parse_file_value_error(self) -> None:
        """Test parse_file raise ValueError."""
        with pytest.raises(ValueError, match="must provide path or file_path"):
            CfnginConfig.parse_file()

    def test_parse_obj(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test model_validate."""
        monkeypatch.setattr(
            MODULE + ".CfnginConfigDefinitionModel.parse_obj",
            lambda x: CfnginConfigDefinitionModel(namespace="success"),  # type: ignore  # noqa: ARG005
        )
        assert CfnginConfig.parse_obj({}).namespace == "success"

    def test_parse_raw(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test parse_raw."""
        mock_resolve_raw_data = MagicMock()
        mock_parse_obj = MagicMock()
        mock_process_package_sources = MagicMock()
        monkeypatch.setattr(CfnginConfig, "resolve_raw_data", mock_resolve_raw_data)
        monkeypatch.setattr(CfnginConfig, "parse_obj", mock_parse_obj)
        monkeypatch.setattr(CfnginConfig, "process_package_sources", mock_process_package_sources)

        data = {"namespace": "test"}
        data_str = yaml.dump(data)
        mock_resolve_raw_data.return_value = data_str
        mock_parse_obj.return_value = data
        mock_process_package_sources.return_value = data_str

        assert (
            CfnginConfig.parse_raw(data_str, skip_package_sources=True, work_dir=tmp_path) == data
        )
        mock_resolve_raw_data.assert_called_once_with(yaml.dump(data), parameters={})
        mock_parse_obj.assert_called_once_with(data)
        mock_process_package_sources.assert_not_called()

        assert (
            CfnginConfig.parse_raw(data_str, parameters={"key": "val"}, work_dir=tmp_path) == data
        )
        mock_resolve_raw_data.assert_called_with(
            yaml.dump(data),
            parameters={"key": "val"},
        )
        mock_process_package_sources.assert_called_once_with(
            data_str, parameters={"key": "val"}, work_dir=tmp_path
        )
        assert mock_parse_obj.call_count == 2

    @patch(MODULE + ".SourceProcessor")
    def test_process_package_sources(
        self, mock_source_processor: MagicMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test process_package_sources."""
        mock_resolve_raw_data = MagicMock(return_value="rendered")
        monkeypatch.setattr(CfnginConfig, "resolve_raw_data", mock_resolve_raw_data)
        mock_source_processor.return_value = mock_source_processor
        mock_source_processor.configs_to_merge = []

        raw_data = "namespace: test"
        merge_data = "merged: value"
        other_config = tmp_path / "other_config.yml"
        other_config.write_text(merge_data)
        assert (
            CfnginConfig.process_package_sources(
                raw_data, parameters={"key": "val"}, work_dir=tmp_path
            )
            == raw_data
        )
        mock_source_processor.assert_called_once_with(
            sources=CfnginPackageSourcesDefinitionModel(),
            cache_dir=tmp_path / "cache",
        )
        mock_source_processor.get_package_sources.assert_called_once_with()
        mock_resolve_raw_data.assert_not_called()

        data = {"namespace": "test", "package_sources": {"git": [{"uri": "something"}]}}
        raw_data = yaml.dump(data)
        mock_source_processor.configs_to_merge = [other_config.resolve()]
        assert (
            CfnginConfig.process_package_sources(
                raw_data, parameters={"key": "val"}, work_dir=tmp_path
            )
            == "rendered"
        )
        mock_source_processor.assert_called_with(
            sources=CfnginPackageSourcesDefinitionModel.parse_obj({"git": [{"uri": "something"}]}),
            cache_dir=tmp_path / "cache",
        )
        assert mock_source_processor.call_count == 2
        expected = data.copy()
        expected["merged"] = "value"
        mock_resolve_raw_data.assert_called_once_with(
            yaml.dump(expected), parameters={"key": "val"}
        )

    def test_resolve_raw_data(self) -> None:
        """Test resolve_raw_data."""
        raw_data = "namespace: ${namespace}"
        expected = "namespace: test"
        assert CfnginConfig.resolve_raw_data(raw_data, parameters={"namespace": "test"}) == expected

    def test_resolve_raw_data_missing_value(self) -> None:
        """Test resolve_raw_data missing value."""
        with pytest.raises(MissingEnvironment) as excinfo:
            CfnginConfig.resolve_raw_data("namespace: ${namespace}")
        assert excinfo.value.key == "namespace"

    def test_resolve_raw_data_ignore_lookup(self) -> None:
        """Test resolve_raw_data ignores lookups."""
        lookup_raw_data = "namespace: ${env something}"
        assert CfnginConfig.resolve_raw_data(lookup_raw_data) == lookup_raw_data


class TestRunwayConfig:
    """Test runway.config.RunwayConfig."""

    def test_find_config_file_yaml(self, tmp_path: Path) -> None:
        """Test file_config_file runway.yaml."""
        runway_yaml = tmp_path / "runway.yaml"
        runway_yaml.touch()
        assert RunwayConfig.find_config_file(tmp_path) == runway_yaml

    def test_find_config_file_yml(self, tmp_path: Path) -> None:
        """Test file_config_file runway.yml."""
        runway_yml = tmp_path / "runway.yml"
        runway_yml.touch()
        assert RunwayConfig.find_config_file(tmp_path) == runway_yml

    def test_find_config_file_ignore_variables(self, tmp_path: Path) -> None:
        """Test file_config_file ignore variables file."""
        runway_yaml = tmp_path / "runway.yaml"
        runway_yaml.touch()
        (tmp_path / "runway.variables.yaml").touch()
        (tmp_path / "runway.variables.yml").touch()
        assert RunwayConfig.find_config_file(tmp_path) == runway_yaml

    def test_find_config_file_not_found(self, tmp_path: Path) -> None:
        """Test file_config_file raise ConfigNotFound."""
        with pytest.raises(ConfigNotFound) as excinfo:
            RunwayConfig.find_config_file(tmp_path)
        assert excinfo.value.path == tmp_path

    def test_find_config_file_value_error(self, tmp_path: Path) -> None:
        """Test file_config_file raise ValueError."""
        (tmp_path / "runway.yaml").touch()
        (tmp_path / "runway.yml").touch()
        with pytest.raises(ValueError, match="more than one"):
            RunwayConfig.find_config_file(tmp_path)

    def test_parse_obj(self) -> None:
        """Test parse_obj."""
        data = {
            "deployments": [
                {
                    "name": "test-deployment",
                    "modules": ["sampleapp.cfn"],
                    "regions": ["us-east-1"],
                }
            ]
        }
        obj = RunwayConfig.parse_obj(data)
        assert isinstance(obj, RunwayConfig)
        assert obj.deployments[0].name == "test-deployment"
        assert obj.deployments[0].modules[0].name == "sampleapp.cfn"
