"""Test runway.config."""
# pylint: disable=no-self-use
from pathlib import Path

import pytest
import yaml
from _pytest.monkeypatch import MonkeyPatch
from mock import MagicMock, patch
from pydantic import ValidationError

from runway.cfngin.exceptions import MissingEnvironment
from runway.config import CfnginConfig
from runway.config.models.cfngin import PackageSources

MODULE = "runway.config"


class TestCfnginConfig:
    """Test runway.config.CfnginConfig."""

    def test_dump(self) -> None:
        """Test dump."""
        data = {"namespace": "test"}
        obj = CfnginConfig.parse_obj(data)
        assert obj.dump() == yaml.dump(
            data, default_flow_style=False, indent=obj.template_indent
        )

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = CfnginConfig(namespace="test")
        assert not obj.cfngin_bucket
        assert not obj.cfngin_bucket_region
        assert obj.cfngin_cache_dir == Path.cwd() / ".runway" / "cache"
        assert obj.log_formats == {}
        assert obj.lookups == {}
        assert obj.mappings == {}
        assert obj.namespace == "test"
        assert obj.namespace_delimiter == "-"
        assert obj.package_sources == PackageSources()
        assert not obj.persistent_graph_key
        assert obj.post_build == []
        assert obj.post_destroy == []
        assert obj.pre_build == []
        assert obj.pre_destroy == []
        assert not obj.service_role
        assert obj.stacks == []
        assert not obj.sys_path
        assert not obj.tags
        assert obj.targets == []
        assert obj.template_indent == 4

    @patch(MODULE + ".register_lookup_handler")
    @patch(MODULE + ".sys")
    def test_load(
        self,
        mock_sys: MagicMock,
        mock_register_lookup_handler: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test load."""
        config = CfnginConfig(namespace="test")

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

    def test_resolve_path_fields(self) -> None:
        """Test _resolve_path_fields."""
        obj = CfnginConfig(
            namespace="test", cfngin_cache_dir="./cache", sys_path="./something",
        )
        assert obj.cfngin_cache_dir.is_absolute()
        assert obj.sys_path.is_absolute()

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            CfnginConfig()
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("namespace",)
        assert errors[0]["msg"] == "field required"

    def test_validate_unique_stack_names(self) -> None:
        """Test _validate_unique_stack_names."""
        data = {
            "namespace": "test",
            "stacks": [
                {"name": "stack0", "class_path": "stack0"},
                {"name": "stack1", "class_path": "stack1"},
            ],
        }
        assert CfnginConfig.parse_obj(data)

    def test_validate_unique_stack_names_invalid(self) -> None:
        """Test _validate_unique_stack_names."""
        with pytest.raises(ValidationError) as excinfo:
            data = {
                "namespace": "test",
                "stacks": [
                    {"name": "stack0", "class_path": "stack0"},
                    {"name": "stack0", "class_path": "stack0"},
                ],
            }
            CfnginConfig.parse_obj(data)
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("stacks",)
        assert errors[0]["msg"] == "Duplicate stack stack0 found at index 0"

    def test_parse_file(self, tmp_path: Path) -> None:
        """Test parse_file."""
        config_yml = tmp_path / "config.yml"
        data = {"namespace": "test"}
        config_yml.write_text(yaml.dump(data))
        config = CfnginConfig.parse_file(config_yml)
        assert config.dict(exclude_unset=True) == data

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
        assert CfnginConfig.parse_obj(data).dict(exclude_unset=True) == expected

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
            sources=PackageSources(), cache_dir=None
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
            sources=PackageSources(git=[{"uri": "something"}]), cache_dir=None
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

    def test_getitem(self) -> None:
        """Test __getitem__."""
        assert CfnginConfig(namespace="test")["namespace"] == "test"
