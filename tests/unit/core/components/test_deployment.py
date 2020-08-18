"""Test runway.core.components.deployment."""
# pylint: disable=no-self-use,protected-access
import logging
import sys

import pytest
from mock import MagicMock, PropertyMock, call, patch

from runway.cfngin.exceptions import UnresolvedVariable
from runway.config import DeploymentDefinition, FutureDefinition, VariablesDefinition
from runway.core.components import Deployment

MODULE = "runway.core.components._deployment"


class TestDeployment(object):
    """Test runway.core.components.deployment.Deployment."""

    def test_init(self, fx_deployments, monkeypatch, runway_context):
        """Test init."""
        definition = fx_deployments.load("min_required")
        mock_merge = MagicMock()
        monkeypatch.setattr(Deployment, "_Deployment__merge_env_vars", mock_merge)

        obj = Deployment(context=runway_context, definition=definition)

        assert isinstance(obj._future, FutureDefinition)
        assert isinstance(obj._variables, VariablesDefinition)
        assert obj.definition == definition
        assert obj.ctx == runway_context
        assert obj.name == "deployment_1"
        mock_merge.assert_called_once_with()

    def test_init_args(self, fx_deployments, runway_context):
        """Test init with args."""
        definition = fx_deployments.load("simple_env_vars_map")
        future = FutureDefinition(strict_environments=True)
        variables = VariablesDefinition(some_key="val")

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
        assert obj.name == "deployment_1"
        assert obj.ctx.env.vars["deployment_var"] == "val"

    @pytest.mark.parametrize(
        "config, expected",
        [
            ("min_required", None),
            ("validate_account", "test"),
            ("validate_account_map", "test"),
        ],
    )
    def test_account_alias_config(
        self, config, expected, fx_deployments, runway_context
    ):
        """Test account_alias_config."""
        obj = Deployment(context=runway_context, definition=fx_deployments.load(config))
        assert obj.account_alias_config == expected

    def test_account_alias_config_none(self, runway_context):
        """Test account_alias_config with incompatible type."""
        obj = Deployment(context=runway_context, definition=MagicMock())
        assert obj.account_alias_config is None

    @pytest.mark.parametrize(
        "config, expected",
        [
            ("min_required", None),
            ("validate_account", "123456789012"),
            ("validate_account_map", "123456789012"),
        ],
    )
    def test_account_id_config(self, config, expected, fx_deployments, runway_context):
        """Test account_id_config."""
        obj = Deployment(context=runway_context, definition=fx_deployments.load(config))
        assert obj.account_id_config == expected

    @pytest.mark.parametrize(
        "config, expected",
        [
            ("min_required", {}),
            (
                "simple_assume_role",
                {
                    "role_arn": "arn:aws:iam::123456789012:role/test",
                    "revert_on_exit": False,
                },
            ),
            (
                "assume_role_verbose",
                {
                    "role_arn": "arn:aws:iam::123456789012:role/test",
                    "revert_on_exit": True,
                    "session_name": "runway-test",
                    "duration_seconds": 300,
                },
            ),
            (
                "assume_role_env_map",
                {
                    "role_arn": "arn:aws:iam::123456789012:role/test",
                    "session_name": "runway-test",
                    "revert_on_exit": False,
                },
            ),
            (
                "assume_role_env_map.2",
                {
                    "role_arn": "arn:aws:iam::123456789012:role/test",
                    "session_name": None,
                    "revert_on_exit": False,
                    "duration_seconds": None,
                },
            ),
            ("assume_role_env_map.3", {}),
        ],
    )
    def test_assume_role_config(self, config, expected, fx_deployments, runway_context):
        """Test assume_role_config."""
        obj = Deployment(context=runway_context, definition=fx_deployments.load(config))
        result = obj.assume_role_config
        assert {k: result[k] for k in sorted(result)} == {
            k: expected[k] for k in sorted(expected)
        }

    def test_env_vars_config_unresolved(
        self, fx_deployments, monkeypatch, runway_context
    ):
        """Test env_vars_config unresolved."""
        expected = {"key": "val"}

        monkeypatch.setattr(
            MODULE + ".merge_nested_environment_dicts", MagicMock(return_value=expected)
        )
        monkeypatch.setattr(
            Deployment, "_Deployment__merge_env_vars", MagicMock(return_value=None)
        )
        monkeypatch.setattr(
            DeploymentDefinition,
            "env_vars",
            PropertyMock(
                side_effect=[UnresolvedVariable("test", MagicMock()), expected]
            ),
        )
        monkeypatch.setattr(
            DeploymentDefinition, "_env_vars", PropertyMock(), raising=False
        )

        raw_deployment = fx_deployments.get("min_required")
        deployment = DeploymentDefinition.from_list([raw_deployment])[0]
        obj = Deployment(context=runway_context, definition=deployment)

        assert obj.env_vars_config == expected
        obj.definition._env_vars.resolve.assert_called_once()

    @pytest.mark.parametrize(
        "config, expected",
        [
            ("min_required", ["us-east-1"]),
            ("min_required_multi", ["us-east-1", "us-west-2"]),
            ("simple_parallel_regions", ["us-east-1", "us-west-2"]),
            ("simple_parallel_regions.2", ["us-east-1", "us-west-2"]),
        ],
    )
    def test_regions(self, config, expected, fx_deployments, runway_context):
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
        self, config, use_concurrent, expected, fx_deployments, runway_context
    ):
        """Test use_async."""
        runway_context._use_concurrent = use_concurrent
        obj = Deployment(context=runway_context, definition=fx_deployments.load(config))
        assert obj.use_async == expected

    def test_deploy(self, fx_deployments, monkeypatch, runway_context):
        """Test deploy."""
        mock_run = MagicMock()
        monkeypatch.setattr(Deployment, "run", mock_run)
        obj = Deployment(
            context=runway_context, definition=fx_deployments.load("min_required")
        )
        assert not obj.deploy()
        mock_run.assert_called_once_with("deploy", "us-east-1")

    @patch(MODULE + ".concurrent.futures")
    @pytest.mark.skipif(sys.version_info.major < 3, reason="only supported by python 3")
    def test_deploy_async(
        self, mock_futures, caplog, fx_deployments, monkeypatch, runway_context
    ):
        """Test deploy async."""
        caplog.set_level(logging.INFO, logger="runway")
        executor = MagicMock()
        mock_futures.ProcessPoolExecutor.return_value = executor
        monkeypatch.setattr(Deployment, "use_async", True)

        obj = Deployment(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_regions"),
        )
        assert not obj.deploy()
        assert (
            "deployment_1:processing regions in parallel... (output will be interwoven)"
            in caplog.messages
        )
        mock_futures.ProcessPoolExecutor.assert_called_once_with(
            max_workers=runway_context.env.max_concurrent_regions
        )
        executor.submit.assert_has_calls(
            [call(obj.run, "deploy", "us-east-1"), call(obj.run, "deploy", "us-west-2")]
        )
        mock_futures.wait.assert_called_once()
        assert executor.submit.return_value.result.call_count == 2

    def test_deploy_sync(self, caplog, fx_deployments, monkeypatch, runway_context):
        """Test deploy sync."""
        caplog.set_level(logging.INFO, logger="runway")
        mock_run = MagicMock()
        monkeypatch.setattr(Deployment, "use_async", False)
        monkeypatch.setattr(Deployment, "run", mock_run)

        obj = Deployment(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_regions"),
        )
        assert not obj.deploy()
        assert "deployment_1:processing regions sequentially..." in caplog.messages
        mock_run.assert_has_calls(
            [call("deploy", "us-east-1"), call("deploy", "us-west-2")]
        )

    @pytest.mark.parametrize("async_used", [(True), (False)])
    def test_destroy(self, async_used, fx_deployments, monkeypatch, runway_context):
        """Test destroy."""
        mock_async = MagicMock()
        monkeypatch.setattr(Deployment, "_Deployment__async", mock_async)
        mock_sync = MagicMock()
        monkeypatch.setattr(Deployment, "_Deployment__sync", mock_sync)
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
    def test_plan(
        self, async_used, caplog, fx_deployments, monkeypatch, runway_context
    ):
        """Test plan."""
        caplog.set_level(logging.INFO, logger="runway")
        mock_async = MagicMock()
        monkeypatch.setattr(Deployment, "_Deployment__async", mock_async)
        mock_sync = MagicMock()
        monkeypatch.setattr(Deployment, "_Deployment__sync", mock_sync)
        runway_context._use_concurrent = async_used
        obj = Deployment(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_regions"),
        )
        assert obj.plan()

        if async_used:
            assert (
                "deployment_1:processing of regions will be done in "
                "parallel during deploy/destroy" in caplog.messages
            )
        mock_async.assert_not_called()
        mock_sync.assert_called_once_with("plan")

    @patch(MODULE + ".aws")
    @patch(MODULE + ".Module")
    def test_run(
        self, mock_module, mock_aws, fx_deployments, monkeypatch, runway_context
    ):
        """Test run."""
        mock_resolve = MagicMock()
        mock_validate = MagicMock()
        definition = fx_deployments.load("min_required")
        monkeypatch.setattr(definition, "resolve", mock_resolve)
        monkeypatch.setattr(Deployment, "validate_account_credentials", mock_validate)
        obj = Deployment(context=runway_context, definition=definition)

        assert not obj.run("deploy", "us-west-2")

        assert runway_context.command == "deploy"
        assert runway_context.env.aws_region == "us-west-2"
        mock_resolve.assert_called_once_with(runway_context, obj._variables)
        mock_validate.assert_called_once_with(runway_context)
        mock_aws.AssumeRole.assert_called_once_with(runway_context)
        mock_aws.AssumeRole().__enter__.assert_called_once()
        mock_module.run_list.assert_called_once_with(
            action="deploy",
            context=runway_context,
            deployment=definition,
            future=obj._future,
            modules=definition.modules,
            variables=obj._variables,
        )

    @patch(MODULE + ".aws")
    @patch(MODULE + ".Module")
    def test_run_async(
        self, mock_module, _mock_aws, fx_deployments, monkeypatch, runway_context
    ):
        """Test run async."""
        mock_resolve = MagicMock()
        definition = fx_deployments.load("simple_parallel_regions")
        runway_context._use_concurrent = True
        monkeypatch.setattr(definition, "resolve", mock_resolve)
        monkeypatch.setattr(Deployment, "validate_account_credentials", MagicMock())
        obj = Deployment(context=runway_context, definition=definition)

        assert not obj.run("destroy", "us-west-2")

        new_ctx = mock_resolve.call_args.args[0]
        assert new_ctx != runway_context
        assert new_ctx.command == "destroy" and runway_context.command != "destroy"
        assert (
            new_ctx.env.aws_region == "us-west-2"
            and runway_context.env.aws_region != "us-west-2"
        )
        assert mock_module.run_list.call_args.kwargs["context"] == new_ctx

    @patch(MODULE + ".aws")
    def test_validate_account_credentials(
        self, mock_aws, caplog, fx_deployments, runway_context
    ):
        """Test validate_account_credentials."""
        caplog.set_level(logging.INFO, logger="runway")
        obj = Deployment(
            context=runway_context, definition=fx_deployments.load("validate_account")
        )

        account = MagicMock()
        account.aliases = ["no-match"]
        account.id = "111111111111"
        mock_aws.AccountDetails.return_value = account
        with pytest.raises(SystemExit) as excinfo:
            assert obj.validate_account_credentials()
        assert excinfo.value.code == 1
        assert 'does not match required account "123456789012"' in "\n".join(
            caplog.messages
        )
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
    def test_run_list(self, action, monkeypatch, runway_context):
        """Test run_list."""
        dep0 = MagicMock()
        dep0.modules = ["module"]
        dep1 = MagicMock()
        dep1.modules = []
        deployments = [dep0, dep1]

        mock_action = MagicMock()
        monkeypatch.setattr(Deployment, action, mock_action)
        mock_vars = MagicMock()

        assert not Deployment.run_list(
            action=action,
            context=runway_context,
            deployments=deployments,
            future=None,
            variables=mock_vars,
        )
        dep0.resolve.assert_called_once_with(
            runway_context, variables=mock_vars, pre_process=True
        )
        dep1.resolve.assert_called_once_with(
            runway_context, variables=mock_vars, pre_process=True
        )
        mock_action.assert_called_once_with()
