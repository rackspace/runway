"""Test runway.module.staticsite.handler."""
# pylint: disable=no-self-use,protected-access
# pyright: basic
from __future__ import annotations

import logging
import string
from typing import TYPE_CHECKING, Any, ClassVar, Dict

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

    delimiter: ClassVar[str] = "!"


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
                    "staticsite_auth_at_edge": "true",
                    "staticsite_user_pool_arn": "arn:aws:cognito-idp:<region>:<account-id>"
                    ":userpool/<pool>",
                },
                "02",
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
                    "staticsite_auth_at_edge": "true",
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
