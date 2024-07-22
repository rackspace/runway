"""Test runway.core.components._module_type."""

# pyright: basic
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from runway.core.components import RunwayModuleType
from runway.module.cdk import CloudDevelopmentKit
from runway.module.cloudformation import CloudFormation
from runway.module.k8s import K8s
from runway.module.serverless import Serverless
from runway.module.staticsite.handler import StaticSite
from runway.module.terraform import Terraform

if TYPE_CHECKING:
    from pathlib import Path

    from runway.config.models.runway import RunwayModuleTypeTypeDef
    from runway.module.base import RunwayModule


class TestRunwayModuleType:
    """Test runway.core.components._module_type.RunwayModuleType."""

    @pytest.mark.parametrize(
        "files, expected",
        [
            (["cdk.json", "package.json"], CloudDevelopmentKit),
            (["any.env", "overlays/"], CloudFormation),
            (["any.yml", "serverless.yml"], CloudFormation),
            (["any.yaml", "package.json"], CloudFormation),
            (["overlays/", "kustomization.yaml", "cdk.json"], K8s),
            (["serverless.yml", "package.json", "cdk.json"], Serverless),
            (["serverless.js", "package.json", "cdk.json"], Serverless),
            (["serverless.ts", "package.json", "cdk.json"], Serverless),
            (["any.tf", "serverless.yml"], Terraform),
        ],
    )
    def test_autodetection(
        self, files: list[str], expected: type[RunwayModule], cd_tmp_path: Path
    ) -> None:
        """Test from autodetection."""
        for file_path in files:
            if file_path.endswith("/"):
                (cd_tmp_path / file_path).mkdir()
            else:
                (cd_tmp_path / file_path).touch()
        result = RunwayModuleType(cd_tmp_path)
        assert result.path == cd_tmp_path
        assert result.class_path == expected.__module__ + "." + expected.__name__
        assert not result.type_str
        assert result.module_class.__name__ == expected.__name__

    def test_autodetection_fail(self, caplog: pytest.LogCaptureFixture, cd_tmp_path: Path) -> None:
        """Test autodetection fail."""
        caplog.set_level(logging.ERROR, logger="runway")
        with pytest.raises(SystemExit) as excinfo:
            assert not RunwayModuleType(cd_tmp_path)
        assert excinfo.value.code == 1
        assert (
            f'module class could not be determined from path "{cd_tmp_path.name}"'
            in caplog.messages
        )

    def test_from_class_path(self, cd_tmp_path: Path) -> None:
        """Test from class_path."""
        result = RunwayModuleType(cd_tmp_path, class_path=CloudFormation.__module__)
        assert result.path == cd_tmp_path
        assert result.class_path == CloudFormation.__module__
        assert not result.type_str
        assert result.module_class.__name__ == CloudFormation.__module__

    @pytest.mark.parametrize(
        "ext, expected",
        [
            ("cdk", CloudDevelopmentKit),
            ("cfn", CloudFormation),
            ("k8s", K8s),
            ("sls", Serverless),
            ("web", StaticSite),
            ("tf", Terraform),
        ],
    )
    def test_from_extension(
        self, ext: str, expected: type[RunwayModule], cd_tmp_path: Path
    ) -> None:
        """Test from path extension."""
        filename = "filename." + ext
        result = RunwayModuleType(cd_tmp_path / filename)
        assert result.module_class == expected

    @pytest.mark.parametrize(
        "type_str, expected",
        [
            ("cdk", CloudDevelopmentKit),
            ("cloudformation", CloudFormation),
            ("kubernetes", K8s),
            ("serverless", Serverless),
            ("static", StaticSite),
            ("terraform", Terraform),
        ],
    )
    def test_from_type_str(
        self,
        type_str: RunwayModuleTypeTypeDef,
        expected: type[RunwayModule],
        cd_tmp_path: Path,
    ) -> None:
        """Test from type_str."""
        result = RunwayModuleType(cd_tmp_path, type_str=type_str)
        assert result.path == cd_tmp_path
        assert result.class_path == expected.__module__ + "." + expected.__name__
        assert result.type_str == type_str
        assert result.module_class == expected
