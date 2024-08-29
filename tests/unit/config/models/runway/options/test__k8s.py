"""Test runway.config.models.runway.options.k8s."""

from __future__ import annotations

from typing import TYPE_CHECKING

from runway.config.models.runway.options.k8s import RunwayK8sModuleOptionsDataModel

if TYPE_CHECKING:
    from pathlib import Path


class TestRunwayK8sModuleOptionsDataModel:
    """Test RunwayK8sModuleOptionsDataModel."""

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayK8sModuleOptionsDataModel()
        assert not obj.kubectl_version
        assert not obj.overlay_path

    def test_init_extra(self) -> None:
        """Test init extra."""
        obj = RunwayK8sModuleOptionsDataModel.model_validate({"invalid": "val"})
        assert "invalid" not in obj.model_dump()

    def test_init(self, tmp_path: Path) -> None:
        """Test init."""
        obj = RunwayK8sModuleOptionsDataModel(kubectl_version="0.13.0", overlay_path=tmp_path)
        assert obj.kubectl_version == "0.13.0"
        assert obj.overlay_path == tmp_path
