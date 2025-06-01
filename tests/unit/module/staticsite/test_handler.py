"""Test runway.module.staticsite.handler."""

from __future__ import annotations

import logging
import platform
import string
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from runway.module.staticsite.handler import StaticSite
from runway.module.staticsite.options import StaticSiteOptions
from runway.module.staticsite.parameters import RunwayStaticSiteModuleParametersDataModel

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from runway.context import RunwayContext


MODULE = "runway.module.staticsite.handler"


class SafeStringTemplate(string.Template):
    """Custom string.Template subclass that changes the ID pattern."""

    delimiter = "!"


class TestStaticSite:
    """Test StaticSite."""

    def test___init__(self, runway_context: RunwayContext, tmp_path: Path) -> None:
        """Test __init__."""
        obj = StaticSite(
            runway_context,
            module_root=tmp_path,
            options={"build_output": "./dist"},
            parameters={"namespace": "test"},
        )
        assert obj.ctx == runway_context
        assert isinstance(obj.options, StaticSiteOptions)
        assert obj.options == StaticSiteOptions.parse_obj({"build_output": "./dist"})
        assert isinstance(obj.parameters, RunwayStaticSiteModuleParametersDataModel)
        assert obj.parameters == RunwayStaticSiteModuleParametersDataModel.model_validate(
            {"namespace": "test"}
        )
        assert obj.path == tmp_path

    @pytest.mark.skipif(platform.system() == "Windows", reason="POSIX path required")
    def test_create_cleanup_yaml(
        self,
        expected_yaml: Path,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test _create_cleanup_yaml."""
        mocker.patch(f"{MODULE}.tempfile", gettempdir=Mock(return_value="./temp"))
        obj = StaticSite(
            runway_context,
            module_root=tmp_path,
            name="test",
            parameters={"namespace": "test"},
        )
        assert (
            obj._create_cleanup_yaml(tmp_path).read_text()
            == (expected_yaml / "cleanup.yaml").read_text()
        )

    @pytest.mark.parametrize(
        "parameters, test_file_number",
        [
            ({}, "01"),
            (
                {
                    "cloudformation_service_role": "aws:arn:iam:123456789012:role/name",
                    "staticsite_role_boundary_arn": "aws:arn:iam:123456789012:policy/name",
                },
                "02",
            ),
        ],
    )
    def test_create_staticsite_yaml(
        self,
        expected_yaml: Path,
        parameters: dict[str, Any],
        runway_context: RunwayContext,
        test_file_number: str,
        tmp_path: Path,
    ) -> None:
        """Test _create_staticsite_yaml."""
        params = {"namespace": "test"}
        params.update(parameters)
        obj = StaticSite(
            runway_context,
            module_root=tmp_path,
            name="test",
            parameters=params,
        )
        assert obj._create_staticsite_yaml(tmp_path).read_text() == SafeStringTemplate(
            (expected_yaml / f"staticsite.{test_file_number}.yaml").read_text()
        ).safe_substitute(module_dir=tmp_path)

    def test_deploy(
        self, mocker: MockerFixture, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test deploy."""
        mock_setup_website_module = mocker.patch.object(
            StaticSite, "_setup_website_module", return_value=None
        )
        obj = StaticSite(
            runway_context,
            module_root=tmp_path,
            parameters={"namespace": "test"},
        )
        assert not obj.deploy()
        mock_setup_website_module.assert_called_once_with(command="deploy")

    def test_destroy(
        self, mocker: MockerFixture, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test destroy."""
        mock_setup_website_module = mocker.patch.object(
            StaticSite, "_setup_website_module", return_value=None
        )
        obj = StaticSite(
            runway_context,
            module_root=tmp_path,
            parameters={"namespace": "test"},
        )
        assert not obj.destroy()
        mock_setup_website_module.assert_called_once_with(command="destroy")

    def test_ensure_valid_environment_config_exit(
        self, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test _ensure_valid_environment_config."""
        with pytest.raises(SystemExit):
            StaticSite(runway_context, module_root=tmp_path, parameters={"namespace": ""})

    def test_get_client_updater_variables(
        self, mocker: MockerFixture, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test _get_client_updater_variables."""
        mock_add_url_scheme = mocker.patch(f"{MODULE}.add_url_scheme", return_value="success")
        obj = StaticSite(
            runway_context,
            module_root=tmp_path,
            name="test",
            parameters={"namespace": "test"},
        )
        site_stack_variables = {"Aliases": ["example.com"]}
        result = obj._get_client_updater_variables("test", site_stack_variables)
        mock_add_url_scheme.assert_called_once_with(site_stack_variables["Aliases"][0])
        assert result["alternate_domains"] == [mock_add_url_scheme.return_value]
        assert "rxref test-" in result["client_id"]
        assert "rxref test::" in result["distribution_domain"]

    def test_init(
        self, caplog: pytest.LogCaptureFixture, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test init."""
        caplog.set_level(logging.WARNING, logger=MODULE)
        obj = StaticSite(runway_context, module_root=tmp_path, parameters={"namespace": "test"})
        assert not obj.init()
        assert f"init not currently supported for {StaticSite.__name__}" in caplog.messages

    def test_plan(
        self, mocker: MockerFixture, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test plan."""
        mock_setup_website_module = mocker.patch.object(
            StaticSite, "_setup_website_module", return_value=None
        )
        obj = StaticSite(
            runway_context,
            module_root=tmp_path,
            parameters={"namespace": "test"},
        )
        assert not obj.plan()
        mock_setup_website_module.assert_called_once_with(command="plan")

    @pytest.mark.parametrize("provided, expected", [("foo", "foo"), ("foo.bar", "foo-bar")])
    def test_sanitized_name(
        self,
        expected: str,
        provided: str,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test sanitized_name."""
        assert (
            StaticSite(
                runway_context,
                module_root=tmp_path,
                name=provided,
                parameters={"namespace": "test"},
            ).sanitized_name
            == expected
        )
