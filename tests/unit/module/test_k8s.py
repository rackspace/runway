"""Test runway.module.k8s."""
# pylint: disable=no-self-use
# pyright: basic
from __future__ import annotations

from typing import TYPE_CHECKING, List

import pytest

from runway.config.models.runway.options.k8s import RunwayK8sModuleOptionsDataModel
from runway.module.k8s import K8s, K8sOptions

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from ..factories import MockRunwayContext

MODULE = "runway.module.k8s"


class TestK8s:
    """Test runway.module.k8s.K8s."""

    def test_skip(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test skip."""
        obj = K8s(runway_context, module_root=tmp_path)  # type: ignore
        assert obj.skip
        obj.options.kustomize_config.parent.mkdir(parents=True, exist_ok=True)
        obj.options.kustomize_config.touch()
        assert not obj.skip


class TestK8sOptions:
    """Test runway.module.k8s.K8sOptions."""

    def test_gen_overlay_dirs(self) -> None:
        """Test gen_overlay_dirs."""
        assert K8sOptions.gen_overlay_dirs("test", "us-east-1") == [
            "test-us-east-1",
            "test",
        ]

    @pytest.mark.parametrize(
        "files, expected",
        [
            (["test-us-east-1/kustomization.yaml"], "test-us-east-1"),
            (
                ["test-us-east-1/kustomization.yaml", "test/kustomization.yaml"],
                "test-us-east-1",
            ),
            (["test/kustomization.yaml"], "test"),
            (["test2/kustomization.yaml"], "test"),
        ],
    )
    def test_get_overlay_dir(
        self, expected: str, files: List[str], tmp_path: Path
    ) -> None:
        """Test get_overlay_dir."""
        for f in files:
            tmp_file = tmp_path / f
            tmp_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_file.touch()
        assert (
            K8sOptions.get_overlay_dir(tmp_path, "test", "us-east-1")
            == tmp_path / expected
        )

    def test_kustomize_config(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test kustomize_config."""
        overlay_path = tmp_path / "overlays" / "test"
        mocker.patch.object(K8sOptions, "overlay_path", overlay_path)
        obj = K8sOptions.parse_obj(
            deploy_environment=runway_context.env, obj={}, path=tmp_path
        )
        assert obj.kustomize_config == overlay_path / "kustomization.yaml"

    def test_overlay_path_found(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test overlay_path found."""
        overlay_path = tmp_path / "overlays" / "test"
        mock_get_overlay_dir = mocker.patch.object(
            K8sOptions, "get_overlay_dir", return_value=overlay_path
        )
        obj = K8sOptions.parse_obj(
            deploy_environment=runway_context.env, obj={}, path=tmp_path
        )
        assert obj.overlay_path == overlay_path
        mock_get_overlay_dir.assert_called_once_with(
            path=tmp_path / "overlays",
            environment=runway_context.env.name,
            region=runway_context.env.aws_region,
        )

    def test_overlay_path_provided(
        self, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test overlay_path provided."""
        overlay_path = tmp_path / "overlays" / "test"
        obj = K8sOptions.parse_obj(
            deploy_environment=runway_context.env,
            obj={"overlay_path": overlay_path},
            path=tmp_path,
        )
        assert obj.overlay_path == overlay_path

    def test_parse_obj(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test parse_obj."""
        config = {"kubectl_version": "0.13.0"}
        obj = K8sOptions.parse_obj(
            deploy_environment=runway_context.env, obj=config, path=tmp_path
        )
        assert isinstance(obj.data, RunwayK8sModuleOptionsDataModel)
        assert obj.data.kubectl_version == config["kubectl_version"]
        assert not obj.data.overlay_path
        assert obj.env == runway_context.env
        assert obj.kubectl_version == config["kubectl_version"]
        assert obj.path == tmp_path
