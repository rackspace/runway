"""Test runway.runway_module_type."""
# pylint: disable=no-self-use
import logging

import pytest

from runway.module.cdk import CloudDevelopmentKit
from runway.module.cloudformation import CloudFormation
from runway.module.k8s import K8s
from runway.module.serverless import Serverless
from runway.module.staticsite import StaticSite
from runway.module.terraform import Terraform
from runway.runway_module_type import RunwayModuleType


class TestRunwayModuleType(object):
    """Test runway.runway_module_type.RunwayModuleType."""

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
    def test_autodetection(self, files, expected, cd_tmp_path):
        """Test from autodetection."""
        for file_path in files:
            if file_path.endswith("/"):
                (cd_tmp_path / file_path).mkdir()
            else:
                (cd_tmp_path / file_path).touch()
        result = RunwayModuleType(str(cd_tmp_path))
        assert result.path == str(cd_tmp_path)
        assert result.class_path == expected.__module__ + "." + expected.__name__
        assert not result.type_str
        assert result.module_class.__name__ == expected.__name__

    def test_autodetection_fail(self, caplog, cd_tmp_path):
        """Test autodetection fail."""
        caplog.set_level(logging.ERROR, logger="runway")
        with pytest.raises(SystemExit) as excinfo:
            assert not RunwayModuleType(str(cd_tmp_path))
        assert excinfo.value.code == 1
        assert (
            'module class could not be determined from path "{}"'.format(
                cd_tmp_path.name
            )
            in caplog.messages
        )

    def test_from_class_path(self, cd_tmp_path):
        """Test from class_path."""
        result = RunwayModuleType(
            str(cd_tmp_path), class_path=CloudFormation.__module__
        )
        assert result.path == str(cd_tmp_path)
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
    def test_from_extension(self, ext, expected, cd_tmp_path):
        """Test from path extension."""
        filename = "filename." + ext
        result = RunwayModuleType(str(cd_tmp_path / filename))
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
    def test_from_type_str(self, type_str, expected, cd_tmp_path):
        """Test from type_str."""
        result = RunwayModuleType(str(cd_tmp_path), type_str=type_str)
        assert result.path == str(cd_tmp_path)
        assert result.class_path == expected.__module__ + "." + expected.__name__
        assert result.type_str == type_str
        assert result.module_class == expected
