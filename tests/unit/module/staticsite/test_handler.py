"""Test runway.module.staticsite.handler."""

# pylint: disable=protected-access
# pyright: basic
from __future__ import annotations

import logging
import platform
import string
from typing import TYPE_CHECKING, Any, Dict

import pytest
from mock import Mock

from runway.module.staticsite.handler import StaticSite
from runway.module.staticsite.options.components import StaticSiteOptions
from runway.module.staticsite.parameters.models import (
    RunwayStaticSiteModuleParametersDataModel,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture
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
        assert obj.parameters == RunwayStaticSiteModuleParametersDataModel.parse_obj(
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
                    "staticsite_auth_at_edge": True,
                    "staticsite_user_pool_arn": "arn:aws:cognito-idp:<region>:<account-id>"
                    ":userpool/<pool>",
                },
                "02",
            ),
            (
                {"staticsite_auth_at_edge": True, "staticsite_create_user_pool": True},
                "03",
            ),
        ],
    )
    def test_create_dependencies_yaml(
        self,
        expected_yaml: Path,
        parameters: Dict[str, Any],
        runway_context: RunwayContext,
        test_file_number: str,
        tmp_path: Path,
    ) -> None:
        """Test _create_dependencies_yaml."""
        params = {"namespace": "test"}
        params.update(parameters)
        obj = StaticSite(
            runway_context,
            module_root=tmp_path,
            name="test",
            parameters=params,
        )
        assert (
            obj._create_dependencies_yaml(tmp_path).read_text()
            == (expected_yaml / f"dependencies.{test_file_number}.yaml").read_text()
        )

    @pytest.mark.parametrize(
        "parameters, test_file_number",
        [
            ({}, "01"),
            (
                {
                    "cloudformation_service_role": "aws:arn:iam:123456789012:role/name",
                    "staticsite_auth_at_edge": True,
                    "staticsite_role_boundary_arn": "aws:arn:iam:123456789012:policy/name",
                    "staticsite_user_pool_arn": "arn:aws:cognito-idp:<region>:<account-id>"
                    ":userpool/<pool>",
                },
                "02",
            ),
        ],
    )
    def test_create_staticsite_yaml(
        self,
        expected_yaml: Path,
        parameters: Dict[str, Any],
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
            parameters={"namespace": "test", "staticsite_auth_at_edge": True},
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
            parameters={"namespace": "test", "staticsite_auth_at_edge": True},
        )
        assert not obj.destroy()
        mock_setup_website_module.assert_called_once_with(command="destroy")

    def test_ensure_auth_at_edge_requirements_exit(
        self, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test _ensure_auth_at_edge_requirements."""
        with pytest.raises(SystemExit):
            StaticSite(
                runway_context,
                module_root=tmp_path,
                parameters={"namespace": "test", "staticsite_auth_at_edge": True},
            )._ensure_auth_at_edge_requirements()

    def test_ensure_cloudfront_with_auth_at_edge_exit(
        self, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test _ensure_cloudfront_with_auth_at_edge."""
        with pytest.raises(SystemExit):
            StaticSite(
                runway_context,
                module_root=tmp_path,
                parameters={
                    "namespace": "test",
                    "staticsite_auth_at_edge": True,
                    "staticsite_cf_disable": True,
                },
            )

    def test_ensure_correct_region_with_auth_at_edge_exit(
        self, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test _ensure_correct_region_with_auth_at_edge."""
        runway_context.env.aws_region = "us-west-2"
        with pytest.raises(SystemExit):
            StaticSite(
                runway_context,
                module_root=tmp_path,
                parameters={"namespace": "test", "staticsite_auth_at_edge": True},
            )

    def test_ensure_valid_environment_config_exit(
        self, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test _ensure_valid_environment_config."""
        with pytest.raises(SystemExit):
            StaticSite(
                runway_context, module_root=tmp_path, parameters={"namespace": ""}
            )

    def test_get_client_updater_variables(
        self, mocker: MockerFixture, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test _get_client_updater_variables."""
        mock_add_url_scheme = mocker.patch(
            f"{MODULE}.add_url_scheme", return_value="success"
        )
        obj = StaticSite(
            runway_context,
            module_root=tmp_path,
            name="test",
            parameters={"namespace": "test", "staticsite_auth_at_edge": True},
        )
        site_stack_variables = {
            "Aliases": ["example.com"],
            "OAuthScopes": "scopes",
            "RedirectPathSignIn": "signin",
            "RedirectPathSignOut": "signout",
        }
        result = obj._get_client_updater_variables("test", site_stack_variables)
        mock_add_url_scheme.assert_called_once_with(site_stack_variables["Aliases"][0])
        assert result["alternate_domains"] == [mock_add_url_scheme.return_value]
        assert "rxref test-" in result["client_id"]
        assert "rxref test::" in result["distribution_domain"]
        assert result["oauth_scopes"] == site_stack_variables["OAuthScopes"]
        assert (
            result["redirect_path_sign_in"]
            == site_stack_variables["RedirectPathSignIn"]
        )
        assert (
            result["redirect_path_sign_out"]
            == site_stack_variables["RedirectPathSignOut"]
        )
        assert (
            result["supported_identity_providers"]
            == obj.parameters.supported_identity_providers
        )

    def test_init(
        self, caplog: LogCaptureFixture, runway_context: RunwayContext, tmp_path: Path
    ) -> None:
        """Test init."""
        caplog.set_level(logging.WARNING, logger=MODULE)
        obj = StaticSite(
            runway_context, module_root=tmp_path, parameters={"namespace": "test"}
        )
        assert not obj.init()
        assert (
            f"init not currently supported for {StaticSite.__name__}" in caplog.messages
        )

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
            parameters={"namespace": "test", "staticsite_auth_at_edge": True},
        )
        assert not obj.plan()
        mock_setup_website_module.assert_called_once_with(command="plan")

    @pytest.mark.parametrize(
        "provided, expected", [("foo", "foo"), ("foo.bar", "foo-bar")]
    )
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
                parameters={"namespace": "test", "staticsite_auth_at_edge": False},
            ).sanitized_name
            == expected
        )
