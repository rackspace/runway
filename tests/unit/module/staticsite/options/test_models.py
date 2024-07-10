"""Test runway.module.staticsite.options.models."""

# pyright: basic
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, cast

import pytest
from pydantic import ValidationError

from runway.module.staticsite.options.models import (
    RunwayStaticSiteExtraFileDataModel,
    RunwayStaticSiteModuleOptionsDataModel,
    RunwayStaticSitePreBuildStepDataModel,
    RunwayStaticSiteSourceHashingDataModel,
    RunwayStaticSiteSourceHashingDirectoryDataModel,
)

MODULE = "runway.module.staticsite.options.models"


class TestRunwayStaticSiteExtraFileDataModel:
    """Test RunwayStaticSiteExtraFileDataModel."""

    @pytest.mark.parametrize(
        "name, expected",
        [
            ("test.json", "application/json"),
            ("test.yaml", "text/yaml"),
            ("test.yml", "text/yaml"),
            ("test", None),
        ],
    )
    def test_autofill_content_type(self, expected: Optional[str], name: str) -> None:
        """Test _autofill_content_type."""
        assert (
            RunwayStaticSiteExtraFileDataModel(content="test", name=name).content_type == expected
        )

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayStaticSiteExtraFileDataModel(content="test-content", name="test-name")
        assert not obj.content_type
        assert obj.content == "test-content"
        assert not obj.file
        assert obj.name == "test-name"

    def test_init_extra(self) -> None:
        """Test init extra."""
        with pytest.raises(ValidationError):
            RunwayStaticSiteExtraFileDataModel(
                content="test-content", name="test-name", invalid="val"  # type: ignore
            )

    def test_init_content_and_file(self, tmp_path: Path) -> None:
        """Test init content and file."""
        with pytest.raises(ValidationError):
            RunwayStaticSiteExtraFileDataModel(
                content="test-content", file=tmp_path, name="test-name"  # type: ignore
            )

    def test_init_content(self) -> None:
        """Test init content."""
        data = {"content_type": "test-data", "content": "content", "name": "test"}
        obj = RunwayStaticSiteExtraFileDataModel(**data)
        assert obj.content_type == data["content_type"]
        assert obj.content == data["content"]
        assert not obj.file
        assert obj.name == data["name"]

    def test_init_file(self, tmp_path: Path) -> None:
        """Test init file."""
        data = {"content_type": "test-data", "file": tmp_path, "name": "test"}
        obj = RunwayStaticSiteExtraFileDataModel.parse_obj(data)
        assert obj.content_type == data["content_type"]
        assert not obj.content
        assert obj.file == data["file"]
        assert obj.name == data["name"]

    @pytest.mark.parametrize(
        "data",
        [
            cast(Dict[str, str], {}),
            {"name": "test"},
            {"content": "test"},
            {"file": "test"},
        ],
    )
    def test_init_required(self, data: Dict[str, Any]) -> None:
        """Test init required fields."""
        with pytest.raises(ValidationError):
            RunwayStaticSiteExtraFileDataModel(**data)


class TestRunwayStaticSiteModuleOptionsDataModel:
    """Test RunwayStaticSiteModuleOptionsDataModel."""

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayStaticSiteModuleOptionsDataModel()
        assert obj.build_output == "./"
        assert not obj.build_steps and isinstance(obj.build_steps, list)
        assert not obj.extra_files and isinstance(obj.extra_files, list)
        assert not obj.pre_build_steps and isinstance(obj.pre_build_steps, list)
        assert obj.source_hashing == RunwayStaticSiteSourceHashingDataModel()

    def test_init_extra(self) -> None:
        """Test init extra."""
        obj = RunwayStaticSiteModuleOptionsDataModel(invalid="val")  # type: ignore
        assert "invalid" not in obj.dict()

    def test_init(self) -> None:
        """Test init."""
        data = {
            "build_output": "./dist",
            "build_steps": ["runway --help"],
            "extra_files": [{"name": "test.json", "content": "{}"}],
            "pre_build_steps": [{"command": "runway --help"}],
            "source_hashing": {"enabled": False},
        }
        obj = RunwayStaticSiteModuleOptionsDataModel(**data)
        assert obj.build_output == data["build_output"]
        assert obj.build_steps == data["build_steps"]
        assert obj.extra_files == [
            RunwayStaticSiteExtraFileDataModel(**data["extra_files"][0])  # type: ignore
        ]
        assert obj.pre_build_steps == [
            RunwayStaticSitePreBuildStepDataModel(**data["pre_build_steps"][0])  # type: ignore
        ]
        assert obj.source_hashing == RunwayStaticSiteSourceHashingDataModel(
            **data["source_hashing"]  # type: ignore
        )


class TestRunwayStaticSitePreBuildStepDataModel:
    """Test RunwayStaticSitePreBuildStepDataModel."""

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayStaticSitePreBuildStepDataModel(command="runway --help")
        assert obj.command == "runway --help"
        assert obj.cwd == Path.cwd()

    def test_init_extra(self) -> None:
        """Test init extra."""
        with pytest.raises(ValidationError):
            RunwayStaticSitePreBuildStepDataModel(
                command="runway --help", invalid="val"  # type: ignore
            )

    def test_init_required(self, tmp_path: Path) -> None:
        """Test init required."""
        with pytest.raises(ValidationError):
            RunwayStaticSitePreBuildStepDataModel(cwd=tmp_path)  # type: ignore

    def test_init(self, tmp_path: Path) -> None:
        """Test init."""
        obj = RunwayStaticSitePreBuildStepDataModel(command="runway --help", cwd=tmp_path)
        assert obj.command == "runway --help"
        assert obj.cwd == tmp_path


class TestRunwayStaticSiteSourceHashingDataModel:
    """Test RunwayStaticSiteSourceHashingDataModel."""

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayStaticSiteSourceHashingDataModel()
        assert obj.directories == [
            RunwayStaticSiteSourceHashingDirectoryDataModel(path="./")  # type: ignore
        ]
        assert obj.enabled is True
        assert not obj.parameter

    def test_init_extra(self) -> None:
        """Test init extra."""
        with pytest.raises(ValidationError):
            RunwayStaticSiteSourceHashingDataModel.parse_obj({"invalid": "test"})

    def test_init(self, tmp_path: Path) -> None:
        """Test init."""
        data = {
            "directories": [{"path": tmp_path}],
            "enabled": False,
            "parameter": "test",
        }
        obj = RunwayStaticSiteSourceHashingDataModel(**data)
        assert obj.directories == [
            RunwayStaticSiteSourceHashingDirectoryDataModel(
                **data["directories"][0]  # type: ignore
            )
        ]
        assert obj.enabled is data["enabled"]
        assert obj.parameter == data["parameter"]


class TestRunwayStaticSiteSourceHashingDirectoryDataModel:
    """Test RunwayStaticSiteSourceHashingDirectoryDataModel."""

    def test_init_default(self, tmp_path: Path) -> None:
        """Test init default."""
        obj = RunwayStaticSiteSourceHashingDirectoryDataModel(path=tmp_path)
        assert not obj.exclusions and isinstance(obj.exclusions, list)
        assert obj.path == tmp_path

    def test_init_extra(self, tmp_path: Path) -> None:
        """Test init extra."""
        with pytest.raises(ValidationError):
            RunwayStaticSiteSourceHashingDirectoryDataModel(
                path=tmp_path, invalid="val"  # type: ignore
            )

    def test_init_required(self) -> None:
        """Test init required."""
        with pytest.raises(ValidationError):
            RunwayStaticSiteSourceHashingDirectoryDataModel(  # type: ignore
                exclusions=["**/*.md"],
            )

    def test_init(self, tmp_path: Path) -> None:
        """Test init."""
        data = {"exclusions": ["**/*.md"], "path": tmp_path}
        obj = RunwayStaticSiteSourceHashingDirectoryDataModel.parse_obj(data)
        assert obj.exclusions == data["exclusions"]
        assert obj.path == data["path"]
