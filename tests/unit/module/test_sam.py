"""Test runway.module.sam."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from runway.core.components import DeployEnvironment
from runway.exceptions import SamNotFound
from runway.module.sam import Sam, SamOptions

from ..factories import MockRunwayContext

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


MODULE = "runway.module.sam"


class TestSamOptions:
    """Test runway.module.sam.SamOptions."""

    def test_init(self) -> None:
        """Test __init__."""
        options = SamOptions.parse_obj(
            {"build_args": ["--use-container"], "deploy_args": ["--guided"], "skip_build": True}
        )
        assert options.build_args == ["--use-container"]
        assert options.deploy_args == ["--guided"]
        assert options.skip_build is True

    def test_init_defaults(self) -> None:
        """Test __init__ with defaults."""
        options = SamOptions.parse_obj({})
        assert options.build_args == []
        assert options.deploy_args == []
        assert options.skip_build is False


class TestSam:
    """Test runway.module.sam.Sam."""

    @property
    def generic_parameters(self) -> dict[str, Any]:
        """Return generic module parameters."""
        return {"test_key": "test-value"}

    @staticmethod
    def get_context(name: str = "test", region: str = "us-east-1") -> MockRunwayContext:
        """Create a basic Runway context object."""
        context = MockRunwayContext(deploy_environment=DeployEnvironment(explicit_name=name))
        context.env.aws_region = region
        return context

    def test_init(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test __init__."""
        mock_check_for_sam = mocker.patch(f"{MODULE}.Sam.check_for_sam")
        module = Sam(self.get_context(), module_root=tmp_path, parameters=self.generic_parameters)
        assert module.name == tmp_path.name
        assert module.stage == "test"
        assert module.region == "us-east-1"
        mock_check_for_sam.assert_called_once()

    def test_cli_args(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test cli_args property."""
        mocker.patch(f"{MODULE}.Sam.check_for_sam")
        module = Sam(self.get_context(), module_root=tmp_path)
        assert module.cli_args == ["--region", "us-east-1"]

    def test_cli_args_debug(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test cli_args property with debug."""
        mocker.patch(f"{MODULE}.Sam.check_for_sam")
        context = self.get_context()
        context.env.vars["DEBUG"] = "1"
        module = Sam(context, module_root=tmp_path)
        assert module.cli_args == ["--region", "us-east-1", "--debug"]

    def test_template_file(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test template_file property."""
        mocker.patch(f"{MODULE}.Sam.check_for_sam")
        template_file = tmp_path / "template.yaml"
        template_file.write_text(
            "AWSTemplateFormatVersion: '2010-09-09'\nTransform: AWS::Serverless-2016-10-31"
        )

        module = Sam(self.get_context(), module_root=tmp_path)
        assert module.template_file == template_file

    def test_template_file_not_found(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test template_file property when no template found."""
        mocker.patch(f"{MODULE}.Sam.check_for_sam")
        module = Sam(self.get_context(), module_root=tmp_path)
        assert module.template_file is None

    def test_config_file(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test config_file property."""
        mocker.patch(f"{MODULE}.Sam.check_for_sam")
        config_file = tmp_path / "samconfig.toml"
        config_file.write_text('[default.deploy.parameters]\nstack_name = "test-stack"')

        module = Sam(self.get_context(), module_root=tmp_path)
        assert module.config_file == config_file

    def test_skip_no_template(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test skip property when no template file."""
        mocker.patch(f"{MODULE}.Sam.check_for_sam")
        module = Sam(self.get_context(), module_root=tmp_path)
        assert module.skip is True

    def test_skip_with_template_and_config(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test skip property with template and config."""
        mocker.patch(f"{MODULE}.Sam.check_for_sam")
        template_file = tmp_path / "template.yaml"
        template_file.write_text(
            "AWSTemplateFormatVersion: '2010-09-09'\nTransform: AWS::Serverless-2016-10-31"
        )
        config_file = tmp_path / "samconfig.toml"
        config_file.write_text('[default.deploy.parameters]\nstack_name = "test-stack"')

        module = Sam(self.get_context(), module_root=tmp_path)
        assert module.skip is False

    def test_gen_cmd_basic(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test gen_cmd method."""
        mocker.patch(f"{MODULE}.Sam.check_for_sam")
        template_file = tmp_path / "template.yaml"
        template_file.write_text(
            "AWSTemplateFormatVersion: '2010-09-09'\nTransform: AWS::Serverless-2016-10-31"
        )

        context = self.get_context()
        context.no_color = False  # Ensure no-color is False
        module = Sam(context, module_root=tmp_path)
        cmd = module.gen_cmd("build")

        expected = ["sam", "build", "--template-file", str(template_file), "--region", "us-east-1"]
        assert cmd == expected

    def test_deploy(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test deploy method."""
        mock_check_for_sam = mocker.patch(f"{MODULE}.Sam.check_for_sam")
        mock_sam_deploy = mocker.patch(f"{MODULE}.Sam.sam_deploy")

        template_file = tmp_path / "template.yaml"
        template_file.write_text(
            "AWSTemplateFormatVersion: '2010-09-09'\nTransform: AWS::Serverless-2016-10-31"
        )
        config_file = tmp_path / "samconfig.toml"
        config_file.write_text('[default.deploy.parameters]\nstack_name = "test-stack"')

        module = Sam(self.get_context(), module_root=tmp_path)
        module.deploy()

        mock_check_for_sam.assert_called_once()
        mock_sam_deploy.assert_called_once()

    def test_deploy_skip(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test deploy method when skipped."""
        mock_check_for_sam = mocker.patch(f"{MODULE}.Sam.check_for_sam")
        mock_sam_deploy = mocker.patch(f"{MODULE}.Sam.sam_deploy")

        module = Sam(self.get_context(), module_root=tmp_path)
        module.deploy()

        mock_check_for_sam.assert_called_once()
        mock_sam_deploy.assert_not_called()

    def test_destroy(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test destroy method."""
        mock_check_for_sam = mocker.patch(f"{MODULE}.Sam.check_for_sam")
        mock_sam_delete = mocker.patch(f"{MODULE}.Sam.sam_delete")

        template_file = tmp_path / "template.yaml"
        template_file.write_text(
            "AWSTemplateFormatVersion: '2010-09-09'\nTransform: AWS::Serverless-2016-10-31"
        )
        config_file = tmp_path / "samconfig.toml"
        config_file.write_text('[default.deploy.parameters]\nstack_name = "test-stack"')

        module = Sam(self.get_context(), module_root=tmp_path)
        module.destroy()

        mock_check_for_sam.assert_called_once()
        mock_sam_delete.assert_called_once()

    def test_check_for_sam_success(self, mocker: MockerFixture) -> None:
        """Test check_for_sam when SAM CLI is available."""
        mock_which = mocker.patch(f"{MODULE}.which", return_value="/usr/local/bin/sam")
        Sam.check_for_sam()
        mock_which.assert_called_once_with("sam")

    def test_check_for_sam_not_found(self, mocker: MockerFixture) -> None:
        """Test check_for_sam when SAM CLI is not available."""
        mock_which = mocker.patch(f"{MODULE}.which", return_value=None)
        with pytest.raises(SamNotFound):
            Sam.check_for_sam()
        mock_which.assert_called_once_with("sam")

    def test_init_method(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test init method."""
        mock_check_for_sam = mocker.patch(f"{MODULE}.Sam.check_for_sam")
        module = Sam(self.get_context(), module_root=tmp_path)
        module.init()  # Should just log a warning
        mock_check_for_sam.assert_called_once()

    def test_plan(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Test plan method."""
        mock_check_for_sam = mocker.patch(f"{MODULE}.Sam.check_for_sam")
        module = Sam(self.get_context(), module_root=tmp_path)
        module.plan()  # Should just log a message
        mock_check_for_sam.assert_called_once()
