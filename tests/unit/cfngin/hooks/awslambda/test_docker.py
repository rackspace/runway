"""Test runway.cfngin.hooks.awslambda.docker."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import pytest
from docker.errors import DockerException, ImageNotFound
from docker.models.images import Image
from docker.types.services import Mount
from mock import Mock, call

from runway.cfngin.hooks.awslambda.constants import (
    AWS_SAM_BUILD_IMAGE_PREFIX,
    DEFAULT_IMAGE_NAME,
    DEFAULT_IMAGE_TAG,
)
from runway.cfngin.hooks.awslambda.docker import DockerDependencyInstaller
from runway.cfngin.hooks.awslambda.models.args import DockerOptions
from runway.exceptions import DockerConnectionRefusedError, DockerExecFailedError

from ....mock_docker.fake_api import FAKE_IMAGE_ID

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture

    from runway.context import CfnginContext


MODULE = "runway.cfngin.hooks.awslambda.docker"


class TestDockerDependencyInstaller:
    """Test DockerDependencyInstaller."""

    def test___init__(self, cfngin_context: CfnginContext, mocker: MockerFixture) -> None:
        """Test __init__."""
        from_env = mocker.patch(f"{MODULE}.DockerClient.from_env", return_value="success")
        options = Mock()
        project = Mock(args=Mock(docker=options))
        obj = DockerDependencyInstaller(project, context=cfngin_context)
        from_env.assert_called_once_with(environment=cfngin_context.env.vars)
        assert obj.client == from_env.return_value
        assert obj.ctx == cfngin_context
        assert obj.options == options
        assert obj.project == project

    def test___init___client(self, mocker: MockerFixture) -> None:
        """Test __init__ passing client."""
        client = Mock()
        from_env = mocker.patch(f"{MODULE}.DockerClient.from_env", return_value="success")
        obj = DockerDependencyInstaller(Mock(), client=client)
        from_env.assert_not_called()
        assert obj.client == client

    def test_bind_mounts(self) -> None:
        """Test bind_mounts."""
        project = Mock(
            cache_dir=None,
            dependency_directory="dependency_directory",
            project_root="project_root",
        )
        obj = DockerDependencyInstaller(project, client=Mock())
        assert obj.bind_mounts == [
            Mount(target="/var/task/lambda", source="dependency_directory", type="bind"),
            Mount(target="/var/task/project", source="project_root", type="bind"),
        ]

    def test_bind_mounts_cache_dir(self) -> None:
        """Test bind_mounts with cache directory."""
        project = Mock(
            cache_dir="cache_dir",
            dependency_directory="dependency_directory",
            project_root="project_root",
        )
        obj = DockerDependencyInstaller(project, client=Mock())
        assert obj.bind_mounts == [
            Mount(target="/var/task/lambda", source="dependency_directory", type="bind"),
            Mount(target="/var/task/project", source="project_root", type="bind"),
            Mount(target="/var/task/cache_dir", source="cache_dir", type="bind"),
        ]

    @pytest.mark.parametrize("name, pull, tag", [("foo", False, "bar"), (None, True, None)])
    def test_build_image(
        self,
        mocker: MockerFixture,
        name: Optional[str],
        pull: bool,
        tag: Optional[str],
        tmp_path: Path,
    ) -> None:
        """Test build_image."""
        docker_file = tmp_path / "Dockerfile"
        docker_file.touch()
        image = Mock(spec=Image, id=FAKE_IMAGE_ID, tags=[f"{name}:{tag}"])
        logs = [{"stream": "foo"}]
        project = Mock(args=Mock(docker=DockerOptions(file=docker_file, pull=pull)))

        mock_build = Mock(return_value=(image, logs))
        mock_log_docker_msg_dict = mocker.patch.object(
            DockerDependencyInstaller, "log_docker_msg_dict"
        )

        assert (
            DockerDependencyInstaller(
                project, client=Mock(images=Mock(build=mock_build))
            ).build_image(
                docker_file,
                **{"name": name} if name else {},
                **{"tag": tag} if tag else {},
            )
            == image
        )
        mock_build.assert_called_once_with(
            dockerfile=docker_file.name,
            forcerm=True,
            path=str(docker_file.parent),
            pull=pull,
        )
        mock_log_docker_msg_dict.assert_called_once_with(logs)
        image.tag.assert_called_once_with(name or DEFAULT_IMAGE_NAME, tag=tag or DEFAULT_IMAGE_TAG)
        image.reload.assert_called_once_with()

    def test_build_image_raise_docker_exception(self, tmp_path: Path) -> None:
        """Test build_image does not catch DockerException."""
        with pytest.raises(DockerException):
            DockerDependencyInstaller(
                Mock(),
                client=Mock(images=Mock(build=Mock(side_effect=DockerException))),
            ).build_image(tmp_path / "Dockerfile")

    def test_environment_variables(self) -> None:
        """Test environment_variables."""
        expected = {"DOCKER_SETTINGS": "something"}
        env_vars = {"FOO": "BAR", "PATH": "/dev/null", **expected}
        ctx = Mock(env=Mock(vars=env_vars))
        obj = DockerDependencyInstaller(Mock(ctx=ctx), client=Mock())
        assert obj.environment_variables == expected

    def test_from_project(self, mocker: MockerFixture) -> None:
        """Test from_project."""
        project = Mock(
            args=Mock(docker=DockerOptions(disabled=False)),
            ctx=Mock(env=Mock(vars={"foo": "bar"})),
        )
        client = Mock(ping=Mock(return_value=True))
        from_env = mocker.patch(f"{MODULE}.DockerClient.from_env", return_value=client)
        result = DockerDependencyInstaller.from_project(project)
        assert isinstance(result, DockerDependencyInstaller)
        from_env.assert_called_once_with(environment=project.ctx.env.vars)
        client.ping.assert_called_once_with()
        assert result.client == client
        assert result.ctx == project.ctx
        assert result.project == project

    def test_from_project_disabled(self) -> None:
        """Test from_project disabled."""
        assert not DockerDependencyInstaller.from_project(
            Mock(args=Mock(docker=DockerOptions(disabled=True)))
        )

    @pytest.mark.parametrize(
        "error_msg",
        [
            "Error while fetching server API version: "  # error from macOS
            "('Connection aborted.', ConnectionRefusedError(61, 'Connection refused'))",
            "Error while fetching server API version: "  # error from Windows
            "(2, 'CreateFile', 'The system cannot find the file specified.')",
        ],
    )
    def test_from_project_handle_connection_refused(
        self, error_msg: str, mocker: MockerFixture
    ) -> None:
        """Test from_project handle DockerException connection refused."""
        mocker.patch(
            f"{MODULE}.DockerClient.from_env",
            side_effect=DockerException(error_msg),
        )
        with pytest.raises(DockerConnectionRefusedError):
            DockerDependencyInstaller.from_project(
                Mock(args=Mock(docker=DockerOptions(disabled=False)))
            )

    def test_from_project_ping_false(self, mocker: MockerFixture) -> None:
        """Test from_project handle DockerException connection refused."""
        project = Mock(
            args=Mock(docker=DockerOptions(disabled=False)),
            ctx=Mock(env=Mock(vars={"foo": "bar"})),
        )
        client = Mock(ping=Mock(return_value=False))
        from_env = mocker.patch(f"{MODULE}.DockerClient.from_env", return_value=client)
        with pytest.raises(DockerConnectionRefusedError):
            DockerDependencyInstaller.from_project(project)
        from_env.assert_called_once_with(environment=project.ctx.env.vars)
        client.ping.assert_called_once_with()

    def test_from_project_raise_docker_error(self, mocker: MockerFixture) -> None:
        """Test from_project raise DockerError when not connection refused."""
        mocker.patch(
            f"{MODULE}.DockerClient.from_env",
            side_effect=DockerException("foobar"),
        )
        with pytest.raises(DockerException):
            DockerDependencyInstaller.from_project(
                Mock(args=Mock(docker=DockerOptions(disabled=False)))
            )

    @pytest.mark.parametrize(
        "image, name, runtime",
        [
            (False, None, False),
            (False, "foo", True),
            (True, None, True),
            (True, "bar", False),
        ],
    )
    def test_image_build_image(
        self,
        image: Optional[str],
        mocker: MockerFixture,
        name: Optional[str],
        runtime: Optional[str],
    ) -> None:
        """Test image build image."""
        project = Mock(args=Mock(docker=Mock(file="foo", image=image), runtime=runtime))
        project.args.docker.name = name
        build_image = mocker.patch.object(
            DockerDependencyInstaller, "build_image", return_value="success"
        )
        obj = DockerDependencyInstaller(project, client=Mock())
        assert obj.image == build_image.return_value
        build_image.assert_called_once_with(project.args.docker.file, name=name)

    @pytest.mark.parametrize(
        "image, runtime, pull",
        [(False, True, False), (True, True, True), (True, False, True)],
    )
    def test_image_pull_image(
        self,
        image: Optional[str],
        mocker: MockerFixture,
        pull: bool,
        runtime: Optional[str],
    ) -> None:
        """Test image pull image."""
        project = Mock(args=Mock(docker=Mock(file=None, image=image, pull=pull), runtime=runtime))
        pull_image = mocker.patch.object(
            DockerDependencyInstaller, "pull_image", return_value="success"
        )
        obj = DockerDependencyInstaller(project, client=Mock())
        assert obj.image == pull_image.return_value
        if image:
            pull_image.assert_called_once_with(
                project.args.docker.image, force=project.args.docker.pull
            )
        else:
            pull_image.assert_called_once_with(
                f"{AWS_SAM_BUILD_IMAGE_PREFIX}{project.args.runtime}:latest",
                force=project.args.docker.pull,
            )

    def test_image_raise_value_error(self, mocker: MockerFixture) -> None:
        """Test image raise ValueError."""
        project = Mock(args=Mock(docker=Mock(file=None, image=None, pull=True), runtime=None))
        build_image = mocker.patch.object(DockerDependencyInstaller, "build_image")
        pull_image = mocker.patch.object(DockerDependencyInstaller, "pull_image")
        obj = DockerDependencyInstaller(project, client=Mock())
        with pytest.raises(ValueError) as excinfo:
            assert not obj.image
        build_image.assert_not_called()
        pull_image.assert_not_called()
        assert str(excinfo.value) == "docker.file, docker.image, or runtime is required"

    def test_install(self, mocker: MockerFixture) -> None:
        """Test install."""
        install_commands = mocker.patch.object(
            DockerDependencyInstaller, "install_commands", ["install"]
        )
        post_install_commands = mocker.patch.object(
            DockerDependencyInstaller, "post_install_commands", ["post-install"]
        )
        pre_install_commands = mocker.patch.object(
            DockerDependencyInstaller, "pre_install_commands", ["pre-install"]
        )
        run_command = mocker.patch.object(
            DockerDependencyInstaller, "run_command", return_value=["foo"]
        )
        obj = DockerDependencyInstaller(Mock(), client=Mock())
        assert not obj.install()
        run_command.assert_has_calls(
            [  # type: ignore
                call(pre_install_commands[0]),
                call(install_commands[0]),
                call(post_install_commands[0]),
            ]
        )

    def test_install_commands(self) -> None:
        """Test install_commands."""
        obj = DockerDependencyInstaller(Mock(), client=Mock())
        assert not obj.install_commands and isinstance(obj.install_commands, list)

    @pytest.mark.parametrize("level", [logging.INFO, logging.DEBUG])
    def test_log_docker_msg_bytes(self, level: int, mocker: MockerFixture) -> None:
        """Test log_docker_msg_bytes."""
        msg = "foobar"
        obj = DockerDependencyInstaller(Mock(), client=Mock())
        docker_logger = mocker.patch.object(obj, "_docker_logger")
        assert obj.log_docker_msg_bytes(iter([f"{msg}\n".encode()]), level=level) == [msg]
        docker_logger.log.assert_called_once_with(level, msg)

    @pytest.mark.parametrize("level", [logging.INFO, logging.DEBUG])
    def test_log_docker_msg_dict(self, level: int, mocker: MockerFixture) -> None:
        """Test log_docker_msg_dict."""
        msgs = ["foo", "bar", "foobar"]
        obj = DockerDependencyInstaller(Mock(), client=Mock())
        docker_logger = mocker.patch.object(obj, "_docker_logger")
        assert (
            obj.log_docker_msg_dict(
                iter(
                    [
                        {"stream": f"{msgs[0]}\n"},
                        {"status": msgs[1]},
                        {"error": msgs[2]},
                    ]
                ),
                level=level,
            )
            == msgs[:-1]
        )
        docker_logger.log.assert_has_calls([call(level, m) for m in msgs[:-1]])  # type: ignore

    def test_post_install_commands(
        self,
        mocker: MockerFixture,
        platform_linux: None,
    ) -> None:
        """Test post_install_commands."""
        # these methods don't exist on windows so they need to be mocked
        getgid = mocker.patch(f"{MODULE}.os.getgid", create=True, return_value=3)
        getuid = mocker.patch(f"{MODULE}.os.getuid", create=True, return_value=4)
        obj = DockerDependencyInstaller(
            Mock(args=Mock(docker=Mock(extra_files=[])), cache_dir=False), client=Mock()
        )
        assert obj.post_install_commands == [
            f"chown -R {getuid.return_value}:{getgid.return_value} /var/task/lambda"
        ]

    def test_post_install_commands_cache_dir(
        self,
        mocker: MockerFixture,
        platform_linux: None,
    ) -> None:
        """Test post_install_commands with cache_dir."""
        # these methods don't exist on windows so they need to be mocked
        getgid = mocker.patch(f"{MODULE}.os.getgid", create=True, return_value=3)
        getuid = mocker.patch(f"{MODULE}.os.getuid", create=True, return_value=4)
        obj = DockerDependencyInstaller(Mock(args=Mock(docker=Mock(extra_files=[]))), client=Mock())
        assert obj.post_install_commands == [
            f"chown -R {getuid.return_value}:{getgid.return_value} /var/task/lambda",
            f"chown -R {getuid.return_value}:{getgid.return_value} /var/task/cache_dir",
        ]

    def test_post_install_commands_extra_files(
        self,
        mocker: MockerFixture,
        platform_linux: None,
    ) -> None:
        """Test post_install_commands with extra_files."""
        # these methods don't exist on windows so they need to be mocked
        getgid = mocker.patch(f"{MODULE}.os.getgid", create=True, return_value=3)
        getuid = mocker.patch(f"{MODULE}.os.getuid", create=True, return_value=4)
        obj = DockerDependencyInstaller(
            Mock(args=Mock(docker=Mock(extra_files=["foo", "bar.*"])), cache_dir=False),
            client=Mock(),
        )
        assert obj.post_install_commands == [
            'sh -c \'cp -v "foo" "/var/task/lambda"\'',
            'sh -c \'cp -v "bar."* "/var/task/lambda"\'',
            f"chown -R {getuid.return_value}:{getgid.return_value} /var/task/lambda",
        ]

    def test_post_install_commands_windows(self, platform_windows: None) -> None:
        """Test post_install_commands Windows."""
        obj = DockerDependencyInstaller(
            Mock(args=Mock(docker=Mock(extra_files=[])), cache_dir=False), client=Mock()
        )
        assert obj.post_install_commands == []

    def test_pre_install_commands(self) -> None:
        """Test pre_install_commands."""
        obj = DockerDependencyInstaller(Mock(cache_dir=False), client=Mock())
        assert obj.pre_install_commands == ["chown -R 0:0 /var/task/lambda"]

    def test_pre_install_commands_cache_dir(self) -> None:
        """Test pre_install_commands with cache_dir."""
        obj = DockerDependencyInstaller(Mock(cache_dir=True), client=Mock())
        assert obj.pre_install_commands == [
            "chown -R 0:0 /var/task/lambda",
            "chown -R 0:0 /var/task/cache_dir",
        ]

    @pytest.mark.parametrize(
        "exists_locally, force",
        [(False, False), (False, True), (True, True), (True, False)],
    )
    def test_pull_image(self, caplog: LogCaptureFixture, exists_locally: bool, force: bool) -> None:
        """Test pull_image."""
        caplog.set_level(logging.INFO, logger=MODULE)
        name = "foo:latest"
        image = Mock(spec=Image, id=FAKE_IMAGE_ID)
        if exists_locally:
            mock_get = Mock(return_value=image)
        else:
            mock_get = Mock(side_effect=ImageNotFound("test"))
        mock_pull = Mock(return_value=image)

        assert (
            DockerDependencyInstaller(
                Mock(), client=Mock(images=Mock(get=mock_get, pull=mock_pull))
            ).pull_image(name, force=force)
            == image
        )

        if force:
            mock_get.assert_not_called()
            assert caplog.messages == [f"pulling docker image {name}..."]
        else:
            mock_get.assert_called_once_with(name)
            if exists_locally:
                mock_pull.assert_not_called()
            else:
                mock_pull.assert_called_once_with(repository=name)
                assert caplog.messages == [f"image not found; pulling docker image {name}..."]

    @pytest.mark.parametrize("command, level", [("foo", logging.DEBUG), ("bar", None)])
    def test_run_command(self, command: str, level: Optional[int], mocker: MockerFixture) -> None:
        """Test run_command."""
        container = Mock(
            logs=Mock(return_value="log-stream"),
            wait=Mock(return_value={"StatusCode": 0}),
        )
        mock_create = Mock(return_value=container)
        mock_log_docker_msg_bytes = mocker.patch.object(
            DockerDependencyInstaller, "log_docker_msg_bytes", return_value=["logs"]
        )
        bind_mounts = mocker.patch.object(DockerDependencyInstaller, "bind_mounts", ["mount"])
        environment_variables = mocker.patch.object(
            DockerDependencyInstaller, "environment_variables", {"foo": "bar"}
        )
        image = mocker.patch.object(DockerDependencyInstaller, "image", "image")

        assert (
            DockerDependencyInstaller(
                Mock(), client=Mock(containers=Mock(create=mock_create))
            ).run_command(command, **{"level": level} if level else {})
            == mock_log_docker_msg_bytes.return_value
        )
        mock_create.assert_called_once_with(
            command=command,
            detach=True,
            environment=environment_variables,
            image=image,
            mounts=bind_mounts,
            working_dir=DockerDependencyInstaller.PROJECT_DIR,
        )
        container.start.assert_called_once_with()
        container.logs.assert_called_once_with(stderr=True, stdout=True, stream=True)
        mock_log_docker_msg_bytes.assert_called_once_with(
            container.logs.return_value,
            level=level or logging.INFO,  # check the default value
        )
        # finally block
        container.wait.assert_called_once_with()
        container.remove.assert_called_once_with(force=True)

    def test_run_command_container_nonzero_exit_code(self, mocker: MockerFixture) -> None:
        """Test run_command container non-zero exit code."""
        error_msg = "error msg"
        container = Mock(
            logs=Mock(return_value="log-stream"),
            start=Mock(side_effect=DockerException),
            wait=Mock(return_value={"StatusCode": 1, "Error": {"Message": error_msg}}),
        )
        mock_log_docker_msg_bytes = mocker.patch.object(
            DockerDependencyInstaller, "log_docker_msg_bytes", return_value=["logs"]
        )
        mocker.patch.object(DockerDependencyInstaller, "bind_mounts", ["mount"])
        mocker.patch.object(DockerDependencyInstaller, "environment_variables", {"foo": "bar"})
        mocker.patch.object(DockerDependencyInstaller, "image", "image")
        with pytest.raises(DockerExecFailedError) as excinfo:
            DockerDependencyInstaller(
                Mock(),
                client=Mock(containers=Mock(create=Mock(return_value=container))),
            ).run_command("foo")
        assert str(excinfo.value) == error_msg
        container.start.assert_called_once_with()
        container.logs.assert_not_called()
        mock_log_docker_msg_bytes.assert_not_called()
        # finally block
        container.wait.assert_called_once_with()
        container.remove.assert_called_once_with(force=True)

    def test_run_command_container_start_error(self, mocker: MockerFixture) -> None:
        """Test run_command container start error."""
        container = Mock(
            logs=Mock(return_value="log-stream"),
            start=Mock(side_effect=DockerException),
            wait=Mock(return_value={}),
        )
        mock_log_docker_msg_bytes = mocker.patch.object(
            DockerDependencyInstaller, "log_docker_msg_bytes", return_value=["logs"]
        )
        mocker.patch.object(DockerDependencyInstaller, "bind_mounts", ["mount"])
        mocker.patch.object(DockerDependencyInstaller, "environment_variables", {"foo": "bar"})
        mocker.patch.object(DockerDependencyInstaller, "image", "image")

        with pytest.raises(DockerException):
            DockerDependencyInstaller(
                Mock(),
                client=Mock(containers=Mock(create=Mock(return_value=container))),
            ).run_command("foo")
        container.start.assert_called_once_with()
        container.logs.assert_not_called()
        mock_log_docker_msg_bytes.assert_not_called()
        # finally block
        container.wait.assert_called_once_with()
        container.remove.assert_called_once_with(force=True)

    def test_runtime(self) -> None:
        """Test runtime."""
        obj = DockerDependencyInstaller(Mock(), client=Mock())
        assert obj.runtime is None
