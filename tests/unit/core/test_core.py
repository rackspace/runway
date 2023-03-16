"""Test runway.core."""

# pyright: basic
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

import pytest
from mock import MagicMock, call

from runway.core import Runway

if TYPE_CHECKING:
    from pytest import LogCaptureFixture, MonkeyPatch
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
        assert result.tests == runway_config.tests
        assert result.ignore_git_branch == runway_config.ignore_git_branch
        assert result.variables == runway_config.variables
        assert result.ctx == runway_context

    def test___init___undetermined_version(
        self,
        caplog: LogCaptureFixture,
        monkeypatch: MonkeyPatch,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test __init__ with unsupported version."""
        monkeypatch.setattr(MODULE + ".__version__", "0.1.0-dev1")
        caplog.set_level(logging.WARNING, logger=MODULE)
        assert Runway(runway_config, runway_context)  # type: ignore
        assert "shallow clone of the repo" in "\n".join(caplog.messages)

    def test___init___unsupported_version(
        self,
        monkeypatch: MonkeyPatch,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test __init__ with unsupported version."""
        monkeypatch.setattr(MODULE + ".__version__", "1.3")
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

    def test_test(
        self,
        caplog: LogCaptureFixture,
        monkeypatch: MonkeyPatch,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test test."""
        caplog.set_level(logging.ERROR, logger="runway")
        test_handlers = {
            "exception": MagicMock(handle=MagicMock(side_effect=Exception())),
            "fail_system_exit_0": MagicMock(
                handle=MagicMock(side_effect=SystemExit(0))
            ),
            "fail_system_exit_1": MagicMock(
                handle=MagicMock(side_effect=SystemExit(1))
            ),
            "success": MagicMock(),
        }
        monkeypatch.setattr(MODULE + "._TEST_HANDLERS", test_handlers)
        obj = Runway(runway_config, runway_context)  # type: ignore

        obj.tests = [  # type: ignore
            MagicMock(type="success"),
            MagicMock(type="fail_system_exit_0"),
        ]
        assert not obj.test()
        assert "the following tests failed" not in "\n".join(caplog.messages)
        test_handlers["success"].handle.assert_called_with(
            obj.tests[0].name, obj.tests[0].args
        )
        test_handlers["fail_system_exit_0"].handle.assert_called_with(
            obj.tests[1].name, obj.tests[1].args
        )
        obj.tests[0].__call__(runway_context, variables=runway_config.variables)
        obj.tests[1].__call__(runway_context, variables=runway_config.variables)

        obj.tests = [  # type: ignore
            MagicMock(type="fail_system_exit_1", required=False),
            MagicMock(type="fail_system_exit_0"),
        ]
        obj.tests[0].name = "fail_system_exit_1"
        with pytest.raises(SystemExit) as excinfo:
            assert not obj.test()
        assert excinfo.value.code == 1
        assert "the following tests failed: fail_system_exit_1" in caplog.messages
        test_handlers["fail_system_exit_1"].handle.assert_called_with(
            obj.tests[0].name, obj.tests[0].args
        )
        test_handlers["fail_system_exit_0"].handle.assert_called_with(
            obj.tests[1].name, obj.tests[1].args
        )
        caplog.clear()

        obj.tests = [  # type: ignore
            MagicMock(type="exception", required=True),
            MagicMock(type="success"),
        ]
        obj.tests[0].name = "exception"
        with pytest.raises(SystemExit) as excinfo:
            assert not obj.test()
        assert excinfo.value.code == 1
        assert "exception:running test (fail)" in caplog.messages
        assert (
            "exception:test required; the remaining tests have been skipped"
            in caplog.messages
        )
        test_handlers["exception"].handle.assert_called_with(
            obj.tests[0].name, obj.tests[0].args
        )
        assert test_handlers["success"].handle.call_count == 1

    def test_test_keyerror(
        self,
        caplog: LogCaptureFixture,
        monkeypatch: MonkeyPatch,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test test with handler not found."""
        caplog.set_level(logging.ERROR, logger="runway")
        test_handlers: Dict[str, Any] = {}
        monkeypatch.setattr(MODULE + "._TEST_HANDLERS", test_handlers)
        obj = Runway(runway_config, runway_context)  # type: ignore

        obj.tests = [MagicMock(type="missing", required=True)]  # type: ignore
        obj.tests[0].name = "test"
        with pytest.raises(SystemExit) as excinfo:
            assert obj.test()
        assert excinfo.value.code == 1
        assert 'test:unable to find handler of type "missing"' in caplog.messages
        assert "the following tests failed: test" not in caplog.messages

        obj.tests[0].required = False
        with pytest.raises(SystemExit) as excinfo:
            assert obj.test()
        assert excinfo.value.code == 1
        assert "the following tests failed: test" in caplog.messages

    def test_test_no_tests(
        self,
        caplog: LogCaptureFixture,
        runway_config: MockRunwayConfig,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test test with no tests defined."""
        caplog.set_level(logging.ERROR, logger="runway")
        obj = Runway(runway_config, runway_context)  # type: ignore
        obj.tests = []
        with pytest.raises(SystemExit) as excinfo:
            assert obj.test()
        assert excinfo.value.code == 1
        assert "no tests defined in runway.yml" in caplog.messages[0]
