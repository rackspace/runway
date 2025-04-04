"""Test runway.core."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call

import pytest
from packaging.specifiers import SpecifierSet

from runway.core import Runway

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from ..factories import MockRunwayConfig, MockRunwayContext

MODULE = "runway.core"


class TestRunway:
    """Test runway.core.Runway."""

    def test___init___(
        self, runway_config: MockRunwayConfig, runway_context: MockRunwayContext
    ) -> None:
        """Test __init__ default values."""
        result = Runway(runway_config, runway_context)  # type: ignore

        assert result.deployments == runway_config.deployments
        assert result.future == runway_config.future
        assert result.ignore_git_branch == runway_config.ignore_git_branch
        assert result.variables == runway_config.variables
        assert result.ctx == runway_context

    def test___init___undetermined_version(
        self,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test __init__ with unsupported version."""
        monkeypatch.setattr(MODULE + ".__version__", "0.1.0-dev1")
        runway_config.runway_version = SpecifierSet(">=1.10")
        caplog.set_level(logging.WARNING, logger=MODULE)
        assert Runway(runway_config, runway_context)  # type: ignore
        assert "shallow clone of the repo" in "\n".join(caplog.messages)

    def test___init___unsupported_version(
        self,
        monkeypatch: pytest.MonkeyPatch,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test __init__ with unsupported version."""
        monkeypatch.setattr(MODULE + ".__version__", "1.3")
        runway_config.runway_version = SpecifierSet(">=1.10")
        with pytest.raises(SystemExit) as excinfo:
            assert not Runway(runway_config, runway_context)  # type: ignore
        assert excinfo.value.code == 1

    def test_deploy(
        self,
        mocker: MockerFixture,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test deploy."""
        mock_deployment = mocker.patch(f"{MODULE}.components.Deployment")
        deployments = MagicMock()
        obj = Runway(runway_config, runway_context)  # type: ignore

        assert not obj.deploy()
        assert runway_context.command == "deploy"
        mock_deployment.run_list.assert_called_once_with(
            action="deploy",
            context=runway_context,
            deployments=runway_config.deployments,
            future=runway_config.future,
            variables=runway_config.variables,
        )
        assert not obj.deploy(deployments)
        mock_deployment.run_list.assert_called_with(
            action="deploy",
            context=runway_context,
            deployments=deployments,
            future=runway_config.future,
            variables=runway_config.variables,
        )

    def test_destroy(
        self,
        mocker: MockerFixture,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test destroy."""
        mock_deployment = mocker.patch(f"{MODULE}.components.Deployment")
        mock_reverse = mocker.patch.object(Runway, "reverse_deployments")
        mock_reverse.return_value = "reversed"
        deployments = MagicMock()
        obj = Runway(runway_config, runway_context)  # type: ignore

        assert not obj.destroy(deployments)
        assert runway_context.command == "destroy"
        mock_deployment.run_list.assert_called_once_with(
            action="destroy",
            context=runway_context,
            deployments=deployments,
            future=runway_config.future,
            variables=runway_config.variables,
        )
        mock_reverse.assert_not_called()
        assert not obj.destroy()
        mock_deployment.run_list.assert_called_with(
            action="destroy",
            context=runway_context,
            deployments="reversed",
            future=runway_config.future,
            variables=runway_config.variables,
        )
        mock_reverse.assert_has_calls(
            [  # type: ignore
                call(runway_config.deployments),
                call(runway_config.deployments),
            ]
        )

    def test_get_env_vars(
        self,
        mocker: MockerFixture,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test get_env_vars."""
        mock_deployment = mocker.patch(f"{MODULE}.components.Deployment")
        mock_deployment.return_value = mock_deployment
        mock_deployment.env_vars_config = {"key": "val"}
        runway_config.deployments = ["deployment_1"]
        obj = Runway(runway_config, runway_context)  # type: ignore

        assert obj.get_env_vars(runway_config.deployments) == {"key": "val"}  # type: ignore
        mock_deployment.assert_called_once_with(
            context=runway_context,
            definition="deployment_1",
            variables=runway_config.variables,
        )

    def test_init(
        self,
        mocker: MockerFixture,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test init."""
        mock_deployment = mocker.patch(f"{MODULE}.components.Deployment")
        deployments = MagicMock()
        obj = Runway(runway_config, runway_context)  # type: ignore

        assert not obj.init()
        assert runway_context.command == "init"
        mock_deployment.run_list.assert_called_once_with(
            action="init",
            context=runway_context,
            deployments=runway_config.deployments,
            future=runway_config.future,
            variables=runway_config.variables,
        )
        assert not obj.init(deployments)
        mock_deployment.run_list.assert_called_with(
            action="init",
            context=runway_context,
            deployments=deployments,
            future=runway_config.future,
            variables=runway_config.variables,
        )

    def test_plan(
        self,
        mocker: MockerFixture,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test plan."""
        mock_deployment = mocker.patch(f"{MODULE}.components.Deployment")
        deployments = MagicMock()
        obj = Runway(runway_config, runway_context)  # type: ignore

        assert not obj.plan()
        assert runway_context.command == "plan"
        mock_deployment.run_list.assert_called_once_with(
            action="plan",
            context=runway_context,
            deployments=runway_config.deployments,
            future=runway_config.future,
            variables=runway_config.variables,
        )
        assert not obj.plan(deployments)
        mock_deployment.run_list.assert_called_with(
            action="plan",
            context=runway_context,
            deployments=deployments,
            future=runway_config.future,
            variables=runway_config.variables,
        )

    def test_reverse_deployments(self) -> None:
        """Test reverse_deployments."""
        deployment_1 = MagicMock(name="deployment_1")
        deployment_2 = MagicMock(name="deployment_2")

        assert Runway.reverse_deployments([deployment_1, deployment_2]) == [
            deployment_2,
            deployment_1,
        ]
        deployment_1.reverse.assert_called_once_with()
        deployment_2.reverse.assert_called_once_with()
