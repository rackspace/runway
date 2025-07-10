"""Test runway.core.components._deployment."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import ANY, MagicMock, Mock, PropertyMock, call

import pytest

from runway.config.components.runway import (
    RunwayDeploymentDefinition,
    RunwayVariablesDefinition,
)
from runway.config.models.runway import RunwayFutureDefinitionModel
from runway.core.components._deployment import Deployment
from runway.exceptions import UnresolvedVariable
from runway.variables import Variable

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.core.type_defs import RunwayActionTypeDef

    from ...factories import MockRunwayContext, YamlLoaderDeployment

MODULE = "runway.core.components._deployment"


class TestDeployment:
    """Test runway.core.components.deployment.Deployment."""

    def test___init__(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test __init__."""
        definition = fx_deployments.load("min_required")
        mock_merge = MagicMock()
        mocker.patch.object(Deployment, "_Deployment__merge_env_vars", mock_merge)

        obj = Deployment(context=runway_context, definition=definition)

        assert isinstance(obj._future, RunwayFutureDefinitionModel)
        assert isinstance(obj._variables, RunwayVariablesDefinition)
        assert obj.definition == definition
        assert obj.ctx == runway_context
        assert obj.name == "unnamed_deployment"
        mock_merge.assert_called_once_with()

    def test___init___args(
        self, fx_deployments: YamlLoaderDeployment, runway_context: MockRunwayContext
    ) -> None:
        """Test __init__ with args."""
        definition = fx_deployments.load("simple_env_vars")
        future = RunwayFutureDefinitionModel()
        variables = RunwayVariablesDefinition.parse_obj({"some_key": "val"})

        obj = Deployment(
            context=runway_context,
            definition=definition,
            future=future,
            variables=variables,
        )

        assert obj._future == future
        assert obj._variables == variables
        assert obj.definition == definition
        assert obj.ctx == runway_context
        assert obj.name == "unnamed_deployment"
        assert obj.ctx.env.vars["deployment_var"] == "val"

    @pytest.mark.parametrize(
        "config, expected",
        [
            ("min_required", {}),
            (
                "simple_assume_role",
                {
                    "duration_seconds": 3600,
                    "revert_on_exit": False,
                    "role_arn": "arn:aws:iam::123456789012:role/test",
                    "session_name": "runway",
                },
            ),
            (
                "assume_role_verbose",
                {
                    "duration_seconds": 900,
                    "revert_on_exit": True,
                    "role_arn": "arn:aws:iam::123456789012:role/test",
                    "session_name": "runway-test",
                },
            ),
        ],
    )
    def test_assume_role_config(
        self,
        config: str,
        expected: dict[str, Any],
        fx_deployments: YamlLoaderDeployment,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test assume_role_config."""
        obj = Deployment(context=runway_context, definition=fx_deployments.load(config))
        assert obj.assume_role_config == expected

    def test_env_vars_config_raise_unresolved_variable(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test env_vars_config raise UnresolvedVariable."""
        mocker.patch.object(Deployment, "_Deployment__merge_env_vars", Mock(return_value=None))
        mocker.patch.object(
            RunwayDeploymentDefinition,
            "env_vars",
            PropertyMock(
                side_effect=UnresolvedVariable(
                    Variable("test", "something", variable_type="runway"),
                    Mock(),
                )
            ),
            create=True,
        )

        with pytest.raises(UnresolvedVariable):
            assert not Deployment(
                context=runway_context,
                definition=RunwayDeploymentDefinition.parse_obj(
                    cast("dict[str, Any]", fx_deployments.get("min_required"))
                ),
            ).env_vars_config

    def test_env_vars_config_unresolved(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test env_vars_config unresolved."""
        expected = {"key": "val"}
        mocker.patch.object(Deployment, "_Deployment__merge_env_vars", Mock(return_value=None))
        mocker.patch.object(
            RunwayDeploymentDefinition,
            "env_vars",
            PropertyMock(
                side_effect=[
                    UnresolvedVariable(
                        Variable("test", "something", variable_type="runway"),
                        Mock(),
                    ),
                    expected,
                ]
            ),
            create=True,
        )
        variable = Mock(value=expected)

        raw_deployment: dict[str, Any] = cast("dict[str, Any]", fx_deployments.get("min_required"))
        deployment = RunwayDeploymentDefinition.parse_obj(raw_deployment)
        obj = Deployment(context=runway_context, definition=deployment)
        obj.definition._vars.update({"env_vars": variable})

        assert obj.env_vars_config == expected
        variable.resolve.assert_called_once()
        assert obj.definition._data["env_vars"] == expected

    @pytest.mark.parametrize(
        "config, expected",
        [
            ("min_required", ["us-east-1"]),
            ("min_required_multi", ["us-east-1", "us-west-2"]),
            ("simple_parallel_regions", ["us-east-1", "us-west-2"]),
            ("simple_parallel_regions.2", ["us-east-1", "us-west-2"]),
        ],
    )
    def test_regions(
        self,
        config: str,
        expected: list[str],
        fx_deployments: YamlLoaderDeployment,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test regions."""
        obj = Deployment(context=runway_context, definition=fx_deployments.load(config))
        assert obj.regions == expected

    @pytest.mark.parametrize(
        "config, use_concurrent, expected",
        [
            ("min_required", True, False),
            ("min_required", False, False),
            ("simple_parallel_regions", True, True),
            ("simple_parallel_regions", False, False),
        ],
    )
    def test_use_async(
        self,
        config: str,
        expected: bool,
        fx_deployments: YamlLoaderDeployment,
        runway_context: MockRunwayContext,
        use_concurrent: bool,
    ) -> None:
        """Test use_async."""
        runway_context._use_concurrent = use_concurrent
        obj = Deployment(context=runway_context, definition=fx_deployments.load(config))
        assert obj.use_async == expected

    def test_deploy(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test deploy."""
        mock_run = MagicMock()
        mocker.patch.object(Deployment, "run", mock_run)
        obj = Deployment(context=runway_context, definition=fx_deployments.load("min_required"))
        assert not obj.deploy()
        mock_run.assert_called_once_with("deploy", "us-east-1")

    def test_deploy_async(
        self,
        caplog: pytest.LogCaptureFixture,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test deploy async."""
        caplog.set_level(logging.INFO, logger="runway")
        mock_futures = mocker.patch(f"{MODULE}.concurrent.futures")
        executor = MagicMock()
        executor.__enter__.return_value = executor
        mock_futures.ProcessPoolExecutor.return_value = executor
        mocker.patch.object(Deployment, "use_async", True)
        mock_mp_context = mocker.patch("multiprocessing.get_context")

        obj = Deployment(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_regions"),
        )
        assert not obj.deploy()
        assert (
            "unnamed_deployment:processing regions in parallel... (output will be interwoven)"
            in caplog.messages
        )
        mock_mp_context.assert_called_once_with("fork")
        mock_futures.ProcessPoolExecutor.assert_called_once_with(
            max_workers=runway_context.env.max_concurrent_regions,
            mp_context=mock_mp_context.return_value,
        )
        executor.submit.assert_has_calls(
            [call(obj.run, "deploy", "us-east-1"), call(obj.run, "deploy", "us-west-2")]
        )
        assert executor.submit.return_value.result.call_count == 2

    def test_deploy_sync(
        self,
        caplog: pytest.LogCaptureFixture,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test deploy sync."""
        caplog.set_level(logging.INFO, logger="runway")
        mock_run = MagicMock()
        mocker.patch.object(Deployment, "use_async", False)
        mocker.patch.object(Deployment, "run", mock_run)

        obj = Deployment(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_regions"),
        )
        assert not obj.deploy()
        assert "unnamed_deployment:processing regions sequentially..." in caplog.messages
        mock_run.assert_has_calls([call("deploy", "us-east-1"), call("deploy", "us-west-2")])

    @pytest.mark.parametrize("async_used", [(True), (False)])
    def test_destroy(
        self,
        async_used: bool,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test destroy."""
        mock_async = MagicMock()
        mocker.patch.object(Deployment, "_Deployment__async", mock_async)
        mock_sync = MagicMock()
        mocker.patch.object(Deployment, "_Deployment__sync", mock_sync)
        runway_context._use_concurrent = async_used
        obj = Deployment(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_regions"),
        )
        assert obj.destroy()

        if async_used:
            mock_async.assert_called_once_with("destroy")
            mock_sync.assert_not_called()
        else:
            mock_async.assert_not_called()
            mock_sync.assert_called_once_with("destroy")

    @pytest.mark.parametrize("async_used", [(True), (False)])
    def test_init(
        self,
        async_used: bool,
        caplog: pytest.LogCaptureFixture,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test init."""
        caplog.set_level(logging.INFO, logger="runway")
        mock_async = MagicMock()
        mocker.patch.object(Deployment, "_Deployment__async", mock_async)
        mock_sync = MagicMock()
        mocker.patch.object(Deployment, "_Deployment__sync", mock_sync)
        runway_context._use_concurrent = async_used
        obj = Deployment(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_regions"),
        )
        assert obj.init()

        if async_used:
            mock_async.assert_called_once_with("init")
            mock_sync.assert_not_called()
        else:
            mock_async.assert_not_called()
            mock_sync.assert_called_once_with("init")

    @pytest.mark.parametrize("async_used", [(True), (False)])
    def test_plan(
        self,
        async_used: bool,
        caplog: pytest.LogCaptureFixture,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test plan."""
        caplog.set_level(logging.INFO, logger="runway")
        mock_async = MagicMock()
        mocker.patch.object(Deployment, "_Deployment__async", mock_async)
        mock_sync = MagicMock()
        mocker.patch.object(Deployment, "_Deployment__sync", mock_sync)
        runway_context._use_concurrent = async_used
        obj = Deployment(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_regions"),
        )
        assert obj.plan()

        if async_used:
            assert (
                "unnamed_deployment:processing of regions will be done in "
                "parallel during deploy/destroy" in caplog.messages
            )
        mock_async.assert_not_called()
        mock_sync.assert_called_once_with("plan")

    def test_run(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test run."""
        mock_aws = mocker.patch(f"{MODULE}.aws")
        mock_module = mocker.patch(f"{MODULE}.Module")
        definition = fx_deployments.load("min_required")
        mock_resolve = mocker.patch.object(definition, "resolve")
        mock_validate = mocker.patch.object(Deployment, "validate_account_credentials")
        obj = Deployment(context=runway_context, definition=definition)

        assert not obj.run("deploy", "us-west-2")

        assert runway_context.command == "deploy"
        assert runway_context.env.aws_region == "us-west-2"
        mock_resolve.assert_called_once_with(runway_context, variables=obj._variables)
        mock_validate.assert_called_once_with(runway_context)
        mock_aws.AssumeRole.assert_called_once_with(runway_context)
        mock_aws.AssumeRole().__enter__.assert_called_once()
        mock_module.run_list.assert_called_once_with(
            action="deploy",
            context=runway_context,
            deployment=definition,
            future=obj._future,
            modules=ANY,  # list of module objects change
            variables=obj._variables,
        )

    def test_run_async(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test run async."""
        mocker.patch(f"{MODULE}.aws")
        mock_module = mocker.patch(f"{MODULE}.Module", MagicMock())
        definition = fx_deployments.load("simple_parallel_regions")
        runway_context._use_concurrent = True
        mock_resolve = mocker.patch.object(definition, "resolve", MagicMock())
        mocker.patch.object(Deployment, "validate_account_credentials")
        obj = Deployment(context=runway_context, definition=definition)

        assert not obj.run("destroy", "us-west-2")

        new_ctx = mock_resolve.call_args.args[0]
        assert new_ctx != runway_context
        assert new_ctx.command == "destroy"
        assert runway_context.command != "destroy"
        assert new_ctx.env.aws_region == "us-west-2"
        assert runway_context.env.aws_region != "us-west-2"
        assert mock_module.run_list.call_args.kwargs["context"] == new_ctx

    def test_validate_account_credentials(
        self,
        caplog: pytest.LogCaptureFixture,
        mocker: MockerFixture,
        fx_deployments: YamlLoaderDeployment,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test validate_account_credentials."""
        caplog.set_level(logging.INFO, logger="runway")
        mock_aws = mocker.patch(f"{MODULE}.aws")
        obj = Deployment(context=runway_context, definition=fx_deployments.load("validate_account"))

        account = MagicMock()
        account.aliases = ["no-match"]
        account.id = "111111111111"
        mock_aws.AccountDetails.return_value = account
        with pytest.raises(SystemExit) as excinfo:
            assert obj.validate_account_credentials()
        assert excinfo.value.code == 1
        assert 'does not match required account "123456789012"' in "\n".join(caplog.messages)
        caplog.clear()
        del excinfo

        account.id = "123456789012"
        with pytest.raises(SystemExit) as excinfo:
            assert obj.validate_account_credentials()
        assert excinfo.value.code == 1
        logs = "\n".join(caplog.messages)
        assert "verified current AWS account matches required account id" in logs
        assert 'do not match required account alias "test"' in logs
        caplog.clear()
        del logs
        del excinfo

        account.aliases = ["test"]
        assert not obj.validate_account_credentials()
        logs = "\n".join(caplog.messages)
        assert "verified current AWS account matches required account id" in logs
        assert "verified current AWS account alias matches required alias" in logs

    @pytest.mark.parametrize("action", [("deploy"), ("destroy")])
    def test_run_list(
        self,
        action: RunwayActionTypeDef,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test run_list."""
        dep0 = MagicMock()
        dep0.modules = ["module"]
        dep1 = MagicMock()
        dep1.modules = []
        deployments = [dep0, dep1]

        mock_action = MagicMock()
        mocker.patch.object(Deployment, action, mock_action)
        mock_vars = MagicMock()

        assert not Deployment.run_list(
            action=action,
            context=runway_context,
            deployments=deployments,  # type: ignore
            future=None,  # type: ignore
            variables=mock_vars,
        )
        dep0.resolve.assert_called_once_with(runway_context, variables=mock_vars, pre_process=True)
        dep1.resolve.assert_called_once_with(runway_context, variables=mock_vars, pre_process=True)
        mock_action.assert_called_once_with()
