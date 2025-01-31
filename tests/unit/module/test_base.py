"""Test runway.module.base."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, cast

import pytest

from runway.exceptions import NpmNotFound
from runway.module.base import NPM_BIN, ModuleOptions, RunwayModule, RunwayModuleNpm

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pytest_mock import MockerFixture
    from pytest_subprocess import FakeProcess

    from ..factories import MockRunwayContext

MODULE = "runway.module.base"


@contextmanager
def does_not_raise() -> Iterator[None]:
    """Use for conditional pytest.raises when using parametrize."""
    yield


class TestModuleOptions:
    """Test runway.module.ModuleOptions."""

    def test_get(self) -> None:
        """Test get."""
        obj = ModuleOptions()
        obj.key = "val"  # type: ignore
        assert obj.get("key") == "val"
        assert obj.get("missing") is None
        assert obj.get("missing", "default") == "default"


class TestRunwayModuleNpm:
    """Test runway.module.base.RunwayModuleNpm."""

    def test_check_for_npm_missing(
        self, caplog: pytest.LogCaptureFixture, mocker: MockerFixture
    ) -> None:
        """Test check_for_npm missing."""
        caplog.set_level(logging.ERROR, logger=MODULE)
        mock_which = mocker.patch(f"{MODULE}.which", return_value=False)
        with pytest.raises(NpmNotFound):
            RunwayModuleNpm.check_for_npm()
        mock_which.assert_called_once_with("npm")
        assert caplog.messages == [
            '"npm" not found in path or is not executable; please ensure it is installed correctly'
        ]

    def test_check_for_npm(self, mocker: MockerFixture) -> None:
        """Test check_for_npm."""
        mock_which = mocker.patch(f"{MODULE}.which", return_value=True)
        assert not RunwayModuleNpm.check_for_npm()
        mock_which.assert_called_once_with("npm")

    def test_init_npm_not_found(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test __init__ raise NpmNotFound."""
        mock_check_for_npm = mocker.patch.object(
            RunwayModuleNpm, "check_for_npm", side_effect=NpmNotFound
        )
        mock_warn_on_boto_env_vars = mocker.patch.object(RunwayModuleNpm, "warn_on_boto_env_vars")
        with pytest.raises(NpmNotFound):
            RunwayModuleNpm(runway_context, module_root=tmp_path)
        mock_check_for_npm.assert_called_once()
        mock_warn_on_boto_env_vars.assert_not_called()

    def test_init(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test __init__."""
        mock_check_for_npm = mocker.patch.object(RunwayModuleNpm, "check_for_npm")
        mock_warn_on_boto_env_vars = mocker.patch.object(RunwayModuleNpm, "warn_on_boto_env_vars")
        obj = RunwayModuleNpm(
            runway_context,
            module_root=tmp_path,
            options={"options": "test"},
            parameters={"parameters": "test"},
        )
        assert obj.ctx == runway_context
        assert not obj.explicitly_enabled
        assert obj.logger
        assert obj.name == tmp_path.name
        assert obj.options == {"options": "test"}
        assert obj.parameters == {"parameters": "test"}
        assert obj.path == tmp_path
        mock_check_for_npm.assert_called_once_with(logger=obj.logger)
        mock_warn_on_boto_env_vars.assert_called_once_with(
            runway_context.env.vars, logger=obj.logger
        )

    def test_log_npm_command(
        self,
        caplog: pytest.LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test log_npm_command."""
        caplog.set_level(logging.DEBUG, logger=MODULE)
        mock_format_npm_command_for_logging = mocker.patch(
            f"{MODULE}.format_npm_command_for_logging", return_value="success"
        )
        mocker.patch.object(RunwayModuleNpm, "check_for_npm")
        mocker.patch.object(RunwayModuleNpm, "warn_on_boto_env_vars")
        obj = RunwayModuleNpm(runway_context, module_root=tmp_path)
        obj.log_npm_command(["test"])
        assert "node command: success" in caplog.messages
        mock_format_npm_command_for_logging.assert_called_once_with(["test"])

    @pytest.mark.parametrize("colorize", [True, False])
    def test_npm_install_ci(
        self,
        caplog: pytest.LogCaptureFixture,
        colorize: bool,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test npm_install ci."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mock_use_npm_ci = mocker.patch(f"{MODULE}.use_npm_ci", return_value=True)
        mocker.patch.object(RunwayModuleNpm, "check_for_npm")
        mocker.patch.object(RunwayModuleNpm, "warn_on_boto_env_vars")
        runway_context.env.ci = True
        runway_context.env.vars["RUNWAY_COLORIZE"] = str(colorize)
        cmd: list[Any] = [NPM_BIN, "ci"]
        if not colorize:
            cmd.append("--no-color")
        fake_process.register_subprocess(cmd, returncode=0)
        RunwayModuleNpm(runway_context, module_root=tmp_path).npm_install()
        mock_use_npm_ci.assert_called_once_with(tmp_path)
        assert "running npm ci..." in caplog.messages
        assert fake_process.call_count(cmd) == 1

    @pytest.mark.parametrize(
        "colorize, is_noninteractive, use_ci",
        [
            (True, False, False),
            (True, True, False),
            (True, False, True),
            (False, True, False),
            (False, False, True),
            (False, False, False),
        ],
    )
    def test_npm_install_install(
        self,
        caplog: pytest.LogCaptureFixture,
        colorize: bool,
        fake_process: FakeProcess,
        is_noninteractive: bool,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
        use_ci: bool,
    ) -> None:
        """Test npm_install install."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mocker.patch(f"{MODULE}.use_npm_ci", return_value=use_ci)
        mocker.patch.object(RunwayModuleNpm, "check_for_npm")
        mocker.patch.object(RunwayModuleNpm, "warn_on_boto_env_vars")
        runway_context.env.ci = is_noninteractive
        runway_context.env.vars["RUNWAY_COLORIZE"] = str(colorize)
        cmd: list[Any] = [NPM_BIN, "install"]
        if not colorize:
            cmd.append("--no-color")
        fake_process.register_subprocess(cmd, returncode=0)
        RunwayModuleNpm(runway_context, module_root=tmp_path).npm_install()
        assert "running npm install..." in caplog.messages
        assert fake_process.call_count(cmd) == 1

    def test_npm_install_skip(
        self,
        caplog: pytest.LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test npm_install skip."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mocker.patch.object(RunwayModuleNpm, "check_for_npm")
        mocker.patch.object(RunwayModuleNpm, "warn_on_boto_env_vars")
        RunwayModuleNpm(
            runway_context, module_root=tmp_path, options={"skip_npm_ci": True}
        ).npm_install()
        assert "skipped npm ci/npm install" in caplog.messages

    def test_package_json_missing(
        self,
        caplog: pytest.LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test package_json_missing."""
        caplog.set_level(logging.DEBUG, logger=MODULE)
        mocker.patch.object(RunwayModuleNpm, "check_for_npm")
        mocker.patch.object(RunwayModuleNpm, "warn_on_boto_env_vars")
        obj = RunwayModuleNpm(context=runway_context, module_root=tmp_path)

        assert obj.package_json_missing()
        assert caplog.messages == ["module is missing package.json"]

        (tmp_path / "package.json").touch()
        assert not obj.package_json_missing()

    def test_warn_on_boto_env_vars(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test warn_on_boto_env_vars."""
        caplog.set_level(logging.WARNING, logger=MODULE)
        RunwayModuleNpm.warn_on_boto_env_vars({"AWS_DEFAULT_PROFILE": "something"})
        assert (
            "AWS_DEFAULT_PROFILE environment variable is set "
            "during use of nodejs-based module and AWS_PROFILE is "
            "not set -- you likely want to set AWS_PROFILE instead"
        ) in caplog.messages

    @pytest.mark.parametrize(
        "env_vars",
        [
            cast(dict[str, str], {}),
            {"AWS_PROFILE": "something"},
            {"AWS_DEFAULT_PROFILE": "something", "AWS_PROFILE": "something"},
        ],
    )
    def test_warn_on_boto_env_vars_no_warn(
        self, caplog: pytest.LogCaptureFixture, env_vars: dict[str, str]
    ) -> None:
        """Test warn_on_boto_env_vars no warn."""
        caplog.set_level(logging.WARNING, logger=MODULE)
        RunwayModuleNpm.warn_on_boto_env_vars(env_vars)
        assert (
            "AWS_DEFAULT_PROFILE environment variable is set "
            "during use of nodejs-based module and AWS_PROFILE is "
            "not set -- you likely want to set AWS_PROFILE instead"
        ) not in caplog.messages


class TestRunwayModule:
    """Test runway.module.base.RunwayModule."""

    def test___init___default(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test __init__ default values."""
        obj = RunwayModule(runway_context, module_root=tmp_path)
        assert not obj.explicitly_enabled
        assert obj.logger
        assert obj.name == tmp_path.name
        assert obj.options == {}
        assert obj.parameters == {}

    def test___init__(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test __init__."""
        obj = RunwayModule(
            runway_context,
            explicitly_enabled=True,
            module_root=tmp_path,
            name="test",
            options={"options": "test"},
            parameters={"parameters": "test"},
            something=None,
        )
        assert obj.ctx == runway_context
        assert obj.explicitly_enabled
        assert obj.logger
        assert obj.name == "test"
        assert obj.options == {"options": "test"}
        assert obj.parameters == {"parameters": "test"}
        assert obj.path == tmp_path
        assert not hasattr(obj, "something")

    def test_deploy(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test deploy."""
        with pytest.raises(NotImplementedError):
            RunwayModule(runway_context, module_root=tmp_path).deploy()

    def test_destroy(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test destroy."""
        with pytest.raises(NotImplementedError):
            RunwayModule(runway_context, module_root=tmp_path).destroy()

    def test_getitem(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test __getitem__."""
        obj = RunwayModule(runway_context, module_root=tmp_path)
        assert obj["path"] == tmp_path

    def test_init(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test init."""
        with pytest.raises(NotImplementedError):
            RunwayModule(runway_context, module_root=tmp_path).init()

    def test_plan(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test plan."""
        with pytest.raises(NotImplementedError):
            RunwayModule(runway_context, module_root=tmp_path).plan()
