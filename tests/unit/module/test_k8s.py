"""Test runway.module.k8s."""

# pyright: basic
from __future__ import annotations

import logging
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, List, Optional

import pytest
import yaml

from runway.config.models.runway.options.k8s import RunwayK8sModuleOptionsDataModel
from runway.exceptions import KubectlVersionNotSpecified
from runway.module.k8s import K8s, K8sOptions

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture
    from pytest_subprocess import FakeProcess

    from runway.module.k8s import KubectlCommandTypeDef

    from ..factories import MockRunwayContext

MODULE = "runway.module.k8s"


class TestK8s:
    """Test runway.module.k8s.K8s."""

    @pytest.mark.parametrize("skip", [False, True])
    def test_deploy(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test deploy."""
        mocker.patch.object(K8s, "skip", skip)
        kubectl_kustomize = mocker.patch.object(K8s, "kubectl_kustomize")
        kubectl_apply = mocker.patch.object(K8s, "kubectl_apply")
        assert not K8s(runway_context, module_root=tmp_path).deploy()
        if skip:
            kubectl_kustomize.assert_not_called()
            kubectl_apply.assert_not_called()
        else:
            kubectl_kustomize.assert_called_once_with()
            kubectl_apply.assert_called_once_with()

    @pytest.mark.parametrize("skip", [False, True])
    def test_destroy(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test destroy."""
        mocker.patch.object(K8s, "skip", skip)
        kubectl_kustomize = mocker.patch.object(K8s, "kubectl_kustomize")
        kubectl_delete = mocker.patch.object(K8s, "kubectl_delete")
        assert not K8s(runway_context, module_root=tmp_path).destroy()
        if skip:
            kubectl_kustomize.assert_not_called()
            kubectl_delete.assert_not_called()
        else:
            kubectl_kustomize.assert_called_once_with()
            kubectl_delete.assert_called_once_with()

    @pytest.mark.parametrize(
        "command, args_list, expected",
        [
            ("apply", None, ["apply", "--kustomize", "overlay_path"]),
            ("auth", ["--something"], ["auth", "--something"]),
            (
                "delete",
                None,
                ["delete", "--kustomize", "overlay_path", "--ignore-not-found=true"],
            ),
            ("kustomize", None, ["kustomize", "overlay_path"]),
        ],
    )
    def test_gen_cmd(
        self,
        args_list: Optional[List[str]],
        command: KubectlCommandTypeDef,
        expected: List[str],
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test gen_command."""
        mocker.patch.object(K8s, "kubectl_bin", "kubectl")
        expected.insert(0, "kubectl")
        assert (
            K8s(
                runway_context,
                module_root=tmp_path,
                options={"overlay_path": "overlay_path"},
            ).gen_cmd(command, args_list)
            == expected
        )

    def test_init(
        self,
        caplog: LogCaptureFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test init."""
        caplog.set_level(logging.WARNING, logger=MODULE)
        obj = K8s(runway_context, module_root=tmp_path)
        assert not obj.init()
        assert f"init not currently supported for {K8s.__name__}" in caplog.messages

    def test_kbenv(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test kbenv."""
        mock_env_mgr = mocker.patch(f"{MODULE}.KBEnvManager", return_value="success")
        overlay_path = mocker.patch(
            f"{MODULE}.K8sOptions.overlay_path", tmp_path / "overlay"
        )
        assert (
            K8s(runway_context, module_root=tmp_path).kbenv == mock_env_mgr.return_value
        )
        mock_env_mgr.assert_called_once_with(tmp_path, overlay_path=overlay_path)

    def test_kubectl_apply(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test kubectl_apply."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mock_gen_cmd = mocker.patch.object(K8s, "gen_cmd", return_value=["apply"])
        mock_run_module_command = mocker.patch(f"{MODULE}.run_module_command")
        obj = K8s(runway_context, module_root=tmp_path)
        assert not obj.kubectl_apply()
        mock_gen_cmd.assert_called_once_with("apply")
        mock_run_module_command.assert_called_once_with(
            cmd_list=mock_gen_cmd.return_value,
            env_vars=runway_context.env.vars,
            logger=obj.logger,
        )
        logs = "\n".join(caplog.messages)
        assert "deploy (in progress)" in logs
        assert "deploy (complete)" in logs

    def test_kubectl_apply_raise_called_process_error(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test kubectl_apply raise CalledProcessError."""
        mocker.patch.object(K8s, "gen_cmd")
        mocker.patch(
            f"{MODULE}.run_module_command", side_effect=CalledProcessError(1, "")
        )
        with pytest.raises(CalledProcessError):
            K8s(runway_context, module_root=tmp_path).kubectl_apply()

    def test_kubectl_bin(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test kubectl_bin."""
        obj = K8s(runway_context, module_root=tmp_path)
        mock_install = mocker.patch.object(obj.kbenv, "install", return_value="success")
        assert obj.kubectl_bin == mock_install.return_value
        mock_install.assert_called_once_with(None)

    def test_kubectl_bin_option(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test kubectl_bin."""
        obj = K8s(
            runway_context, module_root=tmp_path, options={"kubectl_version": "1.22.0"}
        )
        mock_install = mocker.patch.object(obj.kbenv, "install", return_value="success")
        assert obj.kubectl_bin == mock_install.return_value
        mock_install.assert_called_once_with("1.22.0")

    def test_kubectl_bin_handle_version_not_specified(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test kubectl_bin."""
        which = mocker.patch(f"{MODULE}.which", return_value=True)
        obj = K8s(runway_context, module_root=tmp_path)
        mocker.patch.object(
            obj.kbenv, "install", side_effect=KubectlVersionNotSpecified
        )
        assert obj.kubectl_bin == "kubectl"
        which.assert_called_once_with("kubectl")

    def test_kubectl_bin_handle_version_not_specified_exit(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test kubectl_bin."""
        which = mocker.patch(f"{MODULE}.which", return_value=False)
        obj = K8s(runway_context, module_root=tmp_path)
        mocker.patch.object(
            obj.kbenv, "install", side_effect=KubectlVersionNotSpecified
        )
        with pytest.raises(SystemExit):
            assert obj.kubectl_bin
        which.assert_called_once_with("kubectl")

    def test_kubectl_delete(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test kubectl_delete."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mock_gen_cmd = mocker.patch.object(K8s, "gen_cmd", return_value=["delete"])
        mock_run_module_command = mocker.patch(f"{MODULE}.run_module_command")
        obj = K8s(runway_context, module_root=tmp_path)
        assert not obj.kubectl_delete()
        mock_gen_cmd.assert_called_once_with("delete")
        mock_run_module_command.assert_called_once_with(
            cmd_list=mock_gen_cmd.return_value,
            env_vars=runway_context.env.vars,
            logger=obj.logger,
        )
        logs = "\n".join(caplog.messages)
        assert "destroy (in progress)" in logs
        assert "destroy (complete)" in logs

    def test_kubectl_delete_raise_called_process_error(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test kubectl_delete raise CalledProcessError."""
        mocker.patch.object(K8s, "gen_cmd")
        mocker.patch(
            f"{MODULE}.run_module_command", side_effect=CalledProcessError(1, "")
        )
        with pytest.raises(CalledProcessError):
            K8s(runway_context, module_root=tmp_path).kubectl_delete()

    def test_kubectl_kustomize(
        self,
        caplog: LogCaptureFixture,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test kubectl_kustomize."""
        caplog.set_level(logging.DEBUG, logger=MODULE)
        data = {"key": "val"}
        data_string = yaml.dump(data, indent=2)
        gen_cmd = mocker.patch.object(
            K8s, "gen_cmd", return_value=["kubectl", "kustomize"]
        )
        fake_process.register_subprocess(
            gen_cmd.return_value, stdout=data_string, returncode=0
        )
        assert (
            K8s(runway_context, module_root=tmp_path).kubectl_kustomize() == data_string
        )
        assert fake_process.call_count(gen_cmd.return_value) == 1
        logs = "\n".join(caplog.messages)
        assert f"kustomized yaml generated by kubectl:\n\n{data_string}" in logs

    def test_kubectl_kustomize_raise_called_process_error(
        self,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test kubectl_kustomize."""
        gen_cmd = mocker.patch.object(
            K8s, "gen_cmd", return_value=["kubectl", "kustomize"]
        )
        fake_process.register_subprocess(gen_cmd.return_value, returncode=1)
        with pytest.raises(CalledProcessError):
            assert K8s(runway_context, module_root=tmp_path).kubectl_kustomize()
        assert fake_process.call_count(gen_cmd.return_value) == 1

    def test_skip(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test skip."""
        obj = K8s(runway_context, module_root=tmp_path)  # type: ignore
        assert obj.skip
        del obj.skip  # clear cached value
        obj.options.kustomize_config.parent.mkdir(parents=True, exist_ok=True)
        obj.options.kustomize_config.touch()
        assert not obj.skip

    @pytest.mark.parametrize("skip", [False, True])
    def test_plan(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test plan."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mocker.patch.object(K8s, "skip", skip)
        kubectl_kustomize = mocker.patch.object(
            K8s, "kubectl_kustomize", return_value="success"
        )
        assert not K8s(runway_context, module_root=tmp_path).plan()
        if skip:
            kubectl_kustomize.assert_not_called()
        else:
            kubectl_kustomize.assert_called_once_with()
            logs = "\n".join(caplog.messages)
            assert (
                f"kustomized yaml generated by kubectl:\n\n{kubectl_kustomize.return_value}"
                in logs
            )


class TestK8sOptions:
    """Test runway.module.k8s.K8sOptions."""

    def test_gen_overlay_dirs(self) -> None:
        """Test gen_overlay_dirs."""
        assert K8sOptions.gen_overlay_dirs("test", "us-east-1") == [
            "test-us-east-1",
            "test",
        ]

    @pytest.mark.parametrize(
        "files, expected",
        [
            (["test-us-east-1/kustomization.yaml"], "test-us-east-1"),
            (
                ["test-us-east-1/kustomization.yaml", "test/kustomization.yaml"],
                "test-us-east-1",
            ),
            (["test/kustomization.yaml"], "test"),
            (["test2/kustomization.yaml"], "test"),
        ],
    )
    def test_get_overlay_dir(
        self, expected: str, files: List[str], tmp_path: Path
    ) -> None:
        """Test get_overlay_dir."""
        for f in files:
            tmp_file = tmp_path / f
            tmp_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_file.touch()
        assert (
            K8sOptions.get_overlay_dir(tmp_path, "test", "us-east-1")
            == tmp_path / expected
        )

    def test_kustomize_config(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test kustomize_config."""
        overlay_path = tmp_path / "overlays" / "test"
        mocker.patch.object(K8sOptions, "overlay_path", overlay_path)
        obj = K8sOptions.parse_obj(
            deploy_environment=runway_context.env, obj={}, path=tmp_path
        )
        assert obj.kustomize_config == overlay_path / "kustomization.yaml"

    def test_overlay_path_found(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test overlay_path found."""
        overlay_path = tmp_path / "overlays" / "test"
        mock_get_overlay_dir = mocker.patch.object(
            K8sOptions, "get_overlay_dir", return_value=overlay_path
        )
        obj = K8sOptions.parse_obj(
            deploy_environment=runway_context.env, obj={}, path=tmp_path
        )
        assert obj.overlay_path == overlay_path
        mock_get_overlay_dir.assert_called_once_with(
            path=tmp_path / "overlays",
            environment=runway_context.env.name,
            region=runway_context.env.aws_region,
        )

    def test_overlay_path_provided(
        self, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test overlay_path provided."""
        overlay_path = tmp_path / "overlays" / "test"
        obj = K8sOptions.parse_obj(
            deploy_environment=runway_context.env,
            obj={"overlay_path": overlay_path},
            path=tmp_path,
        )
        assert obj.overlay_path == overlay_path

    def test_parse_obj(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test parse_obj."""
        config = {"kubectl_version": "0.13.0"}
        obj = K8sOptions.parse_obj(
            deploy_environment=runway_context.env, obj=config, path=tmp_path
        )
        assert isinstance(obj.data, RunwayK8sModuleOptionsDataModel)
        assert obj.data.kubectl_version == config["kubectl_version"]
        assert not obj.data.overlay_path
        assert obj.env == runway_context.env
        assert obj.kubectl_version == config["kubectl_version"]
        assert obj.path == tmp_path
