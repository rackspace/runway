"""Test runway.config.models.runway.options.terraform."""

import pytest
from pydantic import ValidationError

from runway.config.models.runway.options.terraform import (
    RunwayTerraformArgsDataModel,
    RunwayTerraformBackendConfigDataModel,
    RunwayTerraformModuleOptionsDataModel,
)


class TestRunwayTerraformArgsDataModel:
    """Test RunwayTerraformArgsDataModel."""

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayTerraformArgsDataModel()
        assert not obj.apply
        assert isinstance(obj.apply, list)
        assert not obj.init
        assert isinstance(obj.init, list)
        assert not obj.plan
        assert isinstance(obj.plan, list)

    def test_init_extra(self) -> None:
        """Test init extra."""
        with pytest.raises(ValidationError):
            RunwayTerraformArgsDataModel.model_validate({"invalid": "val"})

    def test_init(self) -> None:
        """Test init."""
        obj = RunwayTerraformArgsDataModel(apply=["-apply"], init=["-init"], plan=["-plan"])
        assert obj.apply == ["-apply"]
        assert obj.init == ["-init"]
        assert obj.plan == ["-plan"]


class TestRunwayTerraformBackendConfigDataModel:
    """Test RunwayTerraformBackendConfigDataModel."""

    def test_bool(self) -> None:
        """Test __bool__."""
        assert RunwayTerraformBackendConfigDataModel(bucket="test")
        assert RunwayTerraformBackendConfigDataModel(dynamodb_table="test")
        assert RunwayTerraformBackendConfigDataModel(bucket="test", dynamodb_table="test")
        assert RunwayTerraformBackendConfigDataModel(
            bucket="test", dynamodb_table="test", workspace_key_prefix="state"
        )
        assert not RunwayTerraformBackendConfigDataModel(region="us-east-1")
        assert not RunwayTerraformBackendConfigDataModel()

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayTerraformBackendConfigDataModel()
        assert not obj.bucket
        assert not obj.dynamodb_table
        assert not obj.region

    def test_init_extra(self) -> None:
        """Test init extra."""
        with pytest.raises(ValidationError):
            RunwayTerraformBackendConfigDataModel.model_validate({"invalid": "val"})

    def test_init(self) -> None:
        """Test init."""
        data = {
            "bucket": "test-bucket",
            "dynamodb_table": "test-table",
            "region": "us-east-1",
            "workspace_key_prefix": "workspace_prefix",
        }
        obj = RunwayTerraformBackendConfigDataModel.model_validate(data)
        assert obj.bucket == data["bucket"]
        assert obj.dynamodb_table == data["dynamodb_table"]
        assert obj.region == data["region"]
        assert obj.workspace_key_prefix == data["workspace_key_prefix"]


class TestRunwayTerraformModuleOptionsDataModel:
    """Test RunwayTerraformModuleOptionsDataModel."""

    def test_convert_args(self) -> None:
        """Test _convert_args."""
        obj = RunwayTerraformModuleOptionsDataModel.model_validate({"args": ["test"]})
        assert obj.args.apply == ["test"]
        assert not obj.args.init
        assert isinstance(obj.args.init, list)
        assert not obj.args.plan
        assert isinstance(obj.args.plan, list)

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayTerraformModuleOptionsDataModel()
        assert not obj.args.apply
        assert not obj.args.init
        assert not obj.args.plan
        assert not obj.backend_config
        assert not obj.version
        assert not obj.workspace
        assert not obj.write_auto_tfvars

    def test_init_extra(self) -> None:
        """Test init extra."""
        assert RunwayTerraformModuleOptionsDataModel.model_validate({"invalid": "val"})

    def test_init(self) -> None:
        """Test init."""
        data = {
            "args": {"init": ["-init"]},
            "terraform_backend_config": {"bucket": "test-bucket"},
            "terraform_version": "0.14.0",
            "terraform_workspace": "default",
            "terraform_write_auto_tfvars": True,
        }
        obj = RunwayTerraformModuleOptionsDataModel.model_validate(data)
        assert obj.args.init == data["args"]["init"]  # type: ignore
        assert (
            obj.backend_config.bucket == data["terraform_backend_config"]["bucket"]  # type: ignore
        )
        assert obj.version == data["terraform_version"]
        assert obj.workspace == data["terraform_workspace"]
        assert obj.write_auto_tfvars == data["terraform_write_auto_tfvars"]
