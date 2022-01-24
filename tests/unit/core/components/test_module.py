"""Test runway.core.components._module."""
# pylint: disable=no-self-use,protected-access,redefined-outer-name,unused-argument
# pyright: basic
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List, Optional, cast

import pytest
import yaml
from mock import MagicMock, call

from runway.core.components import Deployment, Module
from runway.core.components._module import validate_environment

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture

    from ...factories import MockRunwayContext, YamlLoaderDeployment

MODULE = "runway.core.components._module"


@pytest.fixture(scope="function")
def empty_opts_from_file(mocker: MockerFixture) -> None:
    """Empty Module.opts_from_file."""
    mocker.patch.object(Module, "opts_from_file", {})


class TestModule:
    """Test runway.core.components._module.Module."""

    def test___init__(self) -> None:
        """Test __init__."""
        mock_ctx = MagicMock()
        mock_def = MagicMock()
        mock_def.name = "module-name"
        mock_vars = MagicMock()

        mod = Module(context=mock_ctx, definition=mock_def, variables=mock_vars)

        mock_ctx.copy.assert_called_once_with()
        assert mod.ctx == mock_ctx.copy()
        mock_def.resolve.assert_called_once_with(mock_ctx.copy(), variables=mock_vars)
        assert mod.name == "module-name"

    def test_child_modules(
        self, fx_deployments: YamlLoaderDeployment, runway_context: MockRunwayContext
    ) -> None:
        """Test child_modules."""
        deployment = Deployment(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_module"),
        )
        mod0 = Module(
            context=runway_context,
            definition=deployment.definition.modules[0],
            deployment=deployment.definition,
        )
        mod1 = Module(
            context=runway_context,
            definition=deployment.definition.modules[1],
            deployment=deployment.definition,
        )

        assert len(mod0.child_modules) == 2
        assert not mod1.child_modules

        for index, child in enumerate(mod0.child_modules):
            assert isinstance(child, Module)
            # basic checks to ensure the child was setup correctly
            assert child.ctx.env.name == runway_context.env.name
            assert child.definition.path == mod0.definition.child_modules[index].path

    def test_environment_matches_defined(
        self,
        cd_tmp_path: Path,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test environment_matches_defined."""
        mock_validate_environment = mocker.patch(
            f"{MODULE}.validate_environment", return_value="success"
        )
        mocker.patch.object(Module, "environments", {"key": "val"})
        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("min_required").modules[0],
        )
        assert mod.environment_matches_defined == "success"
        mock_validate_environment.assert_called_once_with(
            mod.ctx, {"key": "val"}, logger=mod.logger
        )

    def test_environments_deployment(
        self,
        cd_tmp_path: Path,
        empty_opts_from_file: None,
        fx_deployments: YamlLoaderDeployment,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test environments with opts_from_file."""
        runway_context.env.root_dir = cd_tmp_path
        deployment = fx_deployments.load("environments_map_str")
        mod_def = deployment.modules[0]
        mod_def.environments = {"dev": ["us-east-1"], "prod": ["us-east-1"]}
        mod = Module(context=runway_context, definition=mod_def, deployment=deployment)
        assert mod.environments == {
            "dev": ["us-east-1"],
            "prod": ["us-east-1"],
            "test": "123456789012/us-east-1",
        }

    def test_environments_opts_from_file(
        self,
        cd_tmp_path: Path,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test environments with opts_from_file."""
        runway_context.env.root_dir = cd_tmp_path
        mocker.patch.object(
            Module, "opts_from_file", {"environments": {"test": ["us-east-1"]}}
        )
        deployment = fx_deployments.load("environments_map_str")
        mod = Module(
            context=runway_context,
            definition=deployment.modules[0],
            deployment=deployment,
        )
        assert mod.environments == {
            "test": ["us-east-1"],
            "dev": "012345678901/us-west-2",
        }

    def test_opts_from_file(
        self,
        cd_tmp_path: Path,
        fx_deployments: YamlLoaderDeployment,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test opts_from_file."""
        runway_context.env.root_dir = cd_tmp_path
        mod_dir = cd_tmp_path / "sampleapp-01.cfn"
        mod_dir.mkdir()
        (mod_dir / "runway.module.yml").write_text(yaml.dump({"test": "success"}))
        deployment = fx_deployments.load("simple_module_options")
        mod = Module(
            context=runway_context,
            definition=deployment.modules[0],
            deployment=deployment,
        )
        assert mod.opts_from_file == {"test": "success"}

    def test_path(
        self,
        mocker: MockerFixture,
        fx_deployments: YamlLoaderDeployment,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test path."""
        mock_path = mocker.patch(f"{MODULE}.ModulePath")
        mock_path.parse_obj.return_value = "module-path"
        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("min_required").modules[0],
        )

        assert mod.path == "module-path"
        mock_path.parse_obj.assert_called_once_with(
            mod.definition,
            cache_dir=runway_context.work_dir / "cache",
            deploy_environment=mod.ctx.env,
        )

    def test_payload_with_deployment(
        self,
        cd_tmp_path: Path,
        empty_opts_from_file: None,
        fx_deployments: YamlLoaderDeployment,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test payload with deployment values."""
        runway_context.env.root_dir = cd_tmp_path
        mod_dir = cd_tmp_path / "sampleapp-01.cfn"
        mod_dir.mkdir()
        deployment = fx_deployments.load("simple_module_options")
        mod = Module(
            context=runway_context,
            definition=deployment.modules[0],
            deployment=deployment,
        )
        result = mod.payload

        assert result["options"]["deployment_option"] == "deployment-val"
        assert result["options"]["module_option"] == "module-val"
        assert result["options"]["overlap_option"] == "module-val"

    def test_payload_with_opts_from_file(
        self,
        cd_tmp_path: Path,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test payload."""
        runway_context.env.root_dir = cd_tmp_path
        mocker.patch.object(Module, "environment_matches_defined", True)
        opts = {
            "env_vars": {"local-var": "local-val"},
            "environments": {"test": ["us-east-1"]},
            "options": {"local-opt": "local-opt-val"},
            "parameters": {"local-param": "local-param-val"},
        }
        mocker.patch.object(Module, "opts_from_file", opts)
        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("simple_env_vars").modules[0],
        )
        result = mod.payload

        assert mod.ctx.env.vars["module_var"] == "val"
        assert mod.ctx.env.vars["local-var"] == opts["env_vars"]["local-var"]
        assert result["environments"] == opts["environments"]
        assert result["explicitly_enabled"]
        assert result["options"] == opts["options"]
        assert result["parameters"] == opts["parameters"]

    @pytest.mark.parametrize("validate", [None, False])
    def test_should_skip(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        validate: Optional[bool],
    ) -> None:
        """Test should_skip."""
        mocker.patch.object(Module, "environment_matches_defined", validate)

        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("min_required").modules[0],
        )

        result = mod.should_skip
        assert result is (bool(not validate) if isinstance(validate, bool) else False)

    def test_type(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test type."""
        mock_path = mocker.patch(
            f"{MODULE}.ModulePath", module_root=runway_context.env.root_dir
        )
        mock_type = mocker.patch(f"{MODULE}.RunwayModuleType")
        mock_type.return_value = mock_type
        mocker.patch.object(Module, "path", mock_path)

        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("min_required").modules[0],
        )
        mod.definition.class_path = None

        assert mod.type == mock_type
        mock_type.assert_called_once_with(
            path=cast("Path", mock_path.module_root), class_path=None, type_str=None
        )
        del mod.type

        mod.definition.class_path = "parent.dir.class"
        assert mod.type == mock_type
        mock_type.assert_called_with(
            path=cast("Path", mock_path.module_root),
            class_path="parent.dir.class",
            type_str=None,
        )
        del mod.type

        mod.definition.type = "kubernetes"
        assert mod.type == mock_type
        mock_type.assert_called_with(
            path=cast("Path", mock_path.module_root),
            class_path="parent.dir.class",
            type_str="kubernetes",
        )
        del mod.type

    @pytest.mark.parametrize(
        "config, use_concurrent, expected",
        [
            ("min_required", True, False),
            ("min_required", False, False),
            ("simple_parallel_module", True, True),
            ("simple_parallel_module", False, False),
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
        obj = Module(
            context=runway_context, definition=fx_deployments.load(config).modules[0]
        )
        obj.ctx._use_concurrent = use_concurrent  # type: ignore
        assert obj.use_async == expected

    def test_deploy(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test deploy."""
        mock_run = mocker.patch.object(Module, "run")
        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("min_required").modules[0],
        )
        assert mod.deploy()
        mock_run.assert_called_once_with("deploy")

    def test_deploy_async(
        self,
        caplog: LogCaptureFixture,
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
        mocker.patch.object(Module, "use_async", True)
        mock_mp_context = mocker.patch("multiprocessing.get_context")

        obj = Module(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_module").modules[0],
        )
        assert not obj.deploy()
        assert (
            "parallel_parent:processing modules in parallel... (output "
            "will be interwoven)" in caplog.messages
        )
        mock_mp_context.assert_called_once_with("fork")
        mock_futures.ProcessPoolExecutor.assert_called_once_with(
            max_workers=runway_context.env.max_concurrent_modules,
            mp_context=mock_mp_context.return_value,
        )
        executor.submit.assert_has_calls(
            [
                call(obj.child_modules[0].run, "deploy"),
                call(obj.child_modules[1].run, "deploy"),
            ]
        )
        assert executor.submit.return_value.result.call_count == 2

    def test_deploy_sync(
        self,
        caplog: LogCaptureFixture,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test deploy sync."""
        caplog.set_level(logging.INFO, logger="runway")
        mocker.patch.object(Module, "use_async", False)
        mock_run = mocker.patch.object(Module, "run")

        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_module").modules[0],
        )
        assert not mod.deploy()
        assert "parallel_parent:processing modules sequentially..." in caplog.messages
        mock_run.assert_has_calls([call("deploy"), call("deploy")])  # type: ignore

    @pytest.mark.parametrize("async_used", [(True), (False)])
    def test_destroy(
        self,
        async_used: bool,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test destroy."""
        mock_async = mocker.patch.object(Module, "_Module__async")
        mock_sync = mocker.patch.object(Module, "_Module__sync")
        mocker.patch.object(Module, "use_async", async_used)
        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_module").modules[0],
        )
        assert mod.destroy()

        if async_used:
            mock_async.assert_called_once_with("destroy")
            mock_sync.assert_not_called()
        else:
            mock_async.assert_not_called()
            mock_sync.assert_called_once_with("destroy")

    def test_destroy_no_children(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test destroy with no child modules."""
        mock_async = mocker.patch.object(Module, "_Module__async")
        mock_sync = mocker.patch.object(Module, "_Module__sync")
        mock_run = mocker.patch.object(Module, "run")
        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("min_required").modules[0],
        )
        assert mod.destroy()
        mock_run.assert_called_once_with("destroy")
        mock_async.assert_not_called()
        mock_sync.assert_not_called()

    @pytest.mark.parametrize("async_used", [(True), (False)])
    def test_init(
        self,
        async_used: bool,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test init."""
        mock_async = mocker.patch.object(Module, "_Module__async")
        mock_sync = mocker.patch.object(Module, "_Module__sync")
        mocker.patch.object(Module, "use_async", async_used)
        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_module").modules[0],
        )
        assert mod.init()

        if async_used:
            mock_async.assert_called_once_with("init")
            mock_sync.assert_not_called()
        else:
            mock_async.assert_not_called()
            mock_sync.assert_called_once_with("init")

    def test_init_no_children(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test init with no child modules."""
        mock_async = mocker.patch.object(Module, "_Module__async")
        mock_sync = mocker.patch.object(Module, "_Module__sync")
        mock_run = mocker.patch.object(Module, "run")
        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("min_required").modules[0],
        )
        assert mod.init()
        mock_run.assert_called_once_with("init")
        mock_async.assert_not_called()
        mock_sync.assert_not_called()

    @pytest.mark.parametrize("async_used", [(True), (False)])
    def test_plan(
        self,
        async_used: bool,
        caplog: LogCaptureFixture,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test plan."""
        caplog.set_level(logging.INFO, logger="runway")
        mock_async = mocker.patch.object(Module, "_Module__async")
        mock_sync = mocker.patch.object(Module, "_Module__sync")
        mocker.patch.object(Module, "use_async", async_used)
        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("simple_parallel_module").modules[0],
        )
        assert mod.plan()

        if async_used:
            assert (
                "parallel_parent:processing of modules will be done in "
                "parallel during deploy/destroy" in caplog.messages
            )
        mock_async.assert_not_called()
        mock_sync.assert_called_once_with("plan")

    @pytest.mark.parametrize("async_used", [(True), (False)])
    def test_plan_no_children(
        self,
        async_used: bool,
        caplog: LogCaptureFixture,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test plan with no child modules."""
        caplog.set_level(logging.INFO, logger="runway")
        mock_async = mocker.patch.object(Module, "_Module__async")
        mock_sync = mocker.patch.object(Module, "_Module__sync")
        mock_run = mocker.patch.object(Module, "run")
        mocker.patch.object(Module, "use_async", async_used)
        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("min_required").modules[0],
        )
        assert mod.plan()
        mock_run.assert_called_once_with("plan")
        mock_async.assert_not_called()
        mock_sync.assert_not_called()

    def test_run(
        self,
        empty_opts_from_file: None,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test run."""
        mock_change_dir = mocker.patch(f"{MODULE}.change_dir")
        mock_type = MagicMock()
        mock_inst = MagicMock()
        mock_inst.deploy = MagicMock()
        mock_type.module_class.return_value = mock_inst
        mocker.patch.object(Module, "should_skip", True)
        mocker.patch.object(Module, "path", MagicMock(module_root=tmp_path))
        mocker.patch.object(Module, "type", mock_type)

        mod = Module(
            context=runway_context,
            definition=fx_deployments.load("min_required").modules[0],
        )
        assert not mod.run("deploy")
        mock_change_dir.assert_not_called()

        mocker.patch.object(Module, "should_skip", False)
        assert not mod.run("deploy")
        mock_change_dir.assert_called_once_with(tmp_path)
        mock_type.module_class.assert_called_once_with(
            mod.ctx, module_root=tmp_path, **mod.payload
        )
        mock_inst["deploy"].assert_called_once_with()

        del mock_inst.deploy
        with pytest.raises(SystemExit) as excinfo:
            assert mod.run("deploy")
        assert excinfo.value.code == 1

    def test_run_list(
        self,
        fx_deployments: YamlLoaderDeployment,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test run_list."""
        mock_deploy = mocker.patch.object(Module, "deploy")
        assert not Module.run_list(
            action="deploy",
            context=runway_context,
            modules=fx_deployments.load("simple_parallel_module").modules,
            variables=MagicMock(),
            deployment=MagicMock(),
            future=MagicMock(),
        )
        assert mock_deploy.call_count == 2


@pytest.mark.parametrize(
    "env_def, expected, expected_logs",
    [
        (
            {"invalid"},
            False,
            [f'skipped; unsupported type for environments "{type(set())}"'],  # type: ignore
        ),
        (True, True, ["explicitly enabled"]),
        (False, False, ["skipped; explicitly disabled"]),
        (["123456789012/us-east-1"], True, []),
        (["123456789012/us-east-2"], False, ["skipped; account_id/region mismatch"]),
        ("123456789012/us-east-1", True, []),
        ("123456789012/us-east-2", False, ["skipped; account_id/region mismatch"]),
        ({}, None, ["environment not defined; module will determine deployment"]),
        (
            {"example": "111111111111/us-east-1"},
            False,
            ["skipped; environment not in definition"],
        ),
        ({"test": False}, False, ["skipped; explicitly disabled"]),
        ({"test": True}, True, ["explicitly enabled"]),
        ({"test": "123456789012/us-east-1"}, True, []),
        (
            {"test": "123456789012/us-east-2"},
            False,
            ["skipped; account_id/region mismatch"],
        ),
        ({"test": "123456789012"}, True, []),
        ({"test": "111111111111"}, False, ["skipped; account_id/region mismatch"]),
        ({"test": 123456789012}, True, []),
        ({"test": 111111111111}, False, ["skipped; account_id/region mismatch"]),
        ({"test": "us-east-1"}, True, []),
        ({"test": "us-east-2"}, False, ["skipped; account_id/region mismatch"]),
        (
            {"test": ["123456789012/us-east-1", "123456789012/us-east-2"]},
            True,
            [],
        ),
        (
            {"test": ["123456789012/us-east-2"]},
            False,
            ["skipped; account_id/region mismatch"],
        ),
        ({"test": ["123456789012", "111111111111"]}, True, []),
        ({"test": ["111111111111"]}, False, ["skipped; account_id/region mismatch"]),
        ({"test": [123456789012, 111111111111]}, True, []),
        ({"test": [111111111111]}, False, ["skipped; account_id/region mismatch"]),
        ({"test": ["us-east-1", "us-east-2"]}, True, []),
        ({"test": ["us-east-2"]}, False, ["skipped; account_id/region mismatch"]),
    ],
)
def test_validate_environment(
    caplog: LogCaptureFixture,
    env_def: Any,
    expected_logs: List[str],
    expected: Optional[bool],
    mocker: MockerFixture,
    runway_context: MockRunwayContext,
) -> None:
    """Test validate_environment."""
    caplog.set_level(logging.DEBUG, logger="runway")
    mocker.patch(
        f"{MODULE}.aws",
        **{"AccountDetails.return_value": MagicMock(id="123456789012")},
    )
    assert validate_environment(runway_context, env_def) is expected
    # all() does not give an output that can be used for troubleshooting failures
    for log in expected_logs:
        assert log in caplog.messages
