"""Test ``runway gen-sample`` command."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from runway._cli import cli

if TYPE_CHECKING:
    from pathlib import Path


def test_cdk_csharp(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway gen-sample cdk-csharp`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", "cdk-csharp"])
    assert result.exit_code == 0

    files = [
        "src/HelloCdk/HelloCdk.csproj",
        "src/HelloCdk/HelloConstruct.cs",
        "src/HelloCdk/HelloStack.cs",
        "src/HelloCdk/Program.cs",
        "src/HelloCdk.sln",
        ".gitignore",
        "cdk.json",
        "package.json",
        "README.md",
        "runway.module.yml",
    ]

    module = cd_tmp_path / "sampleapp.cdk"
    assert module.is_dir()

    for file_ in files:
        assert (module / file_).is_file()

    assert caplog.messages == [
        f"Sample C# CDK module created at {module}",
        f"To finish it's setup, change to the {module} directory and execute "
        '"npm install" to generate it\'s lockfile.',
    ]


def test_cdk_py(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway gen-sample cdk-py`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", "cdk-py"])
    assert result.exit_code == 0

    files = [
        "hello/__init__.py",
        "hello/hello_construct.py",
        "hello/hello_stack.py",
        ".gitignore",
        "app.py",
        "package.json",
        "pyproject.toml",
        "poetry.lock",
        "runway.module.yml",
    ]

    module = cd_tmp_path / "sampleapp.cdk"
    assert module.is_dir()

    for file_ in files:
        assert (module / file_).is_file()

    assert caplog.messages == [
        f"Sample CDK module created at {module}",
        f"To finish it's setup, change to the {module} directory and execute "
        '"npm install" to generate it\'s lockfile.',
    ]


def test_cdk_tsc(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway gen-sample cdk-tsc`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", "cdk-tsc"])
    assert result.exit_code == 0

    files = [
        "bin/sample.ts",
        "lib/sample-stack.ts",
        ".gitignore",
        ".npmignore",
        "cdk.json",
        "package.json",
        "README.md",
        "runway.module.yml",
        "tsconfig.json",
    ]

    module = cd_tmp_path / "sampleapp.cdk"
    assert module.is_dir()

    for file_ in files:
        assert (module / file_).is_file()

    assert caplog.messages == [
        f"Sample CDK module created at {module}",
        f"To finish it's setup, change to the {module} directory and execute "
        '"npm install" to generate it\'s lockfile.',
    ]


def test_cfn(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway gen-sample cfn`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", "cfn"])
    assert result.exit_code == 0

    files = ["templates/tf_state.yml", "dev-us-east-1.env", "stacks.yaml"]

    module = cd_tmp_path / "sampleapp.cfn"
    assert module.is_dir()

    for file_ in files:
        assert (module / file_).is_file()

    assert caplog.messages == [f"Sample CloudFormation module created at {module}"]


def test_cfngin(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway gen-sample cfngin`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", "cfngin"])
    assert result.exit_code == 0

    files = [
        "tfstate_blueprints/__init__.py",
        "tfstate_blueprints/tf_state.py",
        "dev-us-east-1.env",
        "stacks.yaml",
    ]

    module = cd_tmp_path / "sampleapp.cfn"
    assert module.is_dir()

    for file_ in files:
        assert (module / file_).is_file()

    assert caplog.messages == [f"Sample CFNgin module created at {module}"]


def test_sls_py(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway gen-sample sls-py`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", "sls-py"])
    assert result.exit_code == 0

    files = [
        "hello_world/__init__.py",
        ".gitignore",
        "__init__.py",
        "config-dev-us-east-1.json",
        "package.json",
        "pyproject.toml",
        "poetry.lock",
        "serverless.yml",
    ]

    module = cd_tmp_path / "sampleapp.sls"
    assert module.is_dir()

    for file_ in files:
        assert (module / file_).is_file()

    assert caplog.messages == [
        f"Sample Serverless module created at {module}",
        f"To finish it's setup, change to the {module} directory and execute "
        '"npm install" to generate it\'s lockfile.',
    ]


def test_sls_tsc(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway gen-sample sls-tsc`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", "sls-tsc"])
    assert result.exit_code == 0

    files = [
        "src/helloWorld.ts",
        "src/helloWorld.test.ts",
        ".gitignore",
        ".eslintignore",
        ".eslintrc.js",
        "jest.config.js",
        "package.json",
        "serverless.yml",
        "tsconfig.json",
        "webpack.config.js",
    ]

    module = cd_tmp_path / "sampleapp.sls"
    assert module.is_dir()

    for file_ in files:
        assert (module / file_).is_file()

    assert caplog.messages == [
        f"Sample Serverless module created at {module}",
        f"To finish it's setup, change to the {module} directory and execute "
        '"npm install" to generate it\'s lockfile.',
    ]


def test_static_angular(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway gen-sample static-angular`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", "static-angular"])
    assert result.exit_code == 0

    files = [
        "sampleapp.web/e2e/src/app.e2e-spec.ts",
        "sampleapp.web/e2e/src/app.po.ts",
        "sampleapp.web/e2e/protractor.conf.js",
        "sampleapp.web/e2e/tsconfig.json",
        "sampleapp.web/src/app/app-routing.module.ts",
        "sampleapp.web/src/app/app.component.css",
        "sampleapp.web/src/app/app.component.html",
        "sampleapp.web/src/app/app.component.ts",
        "sampleapp.web/src/app/app.component.spec.ts",
        "sampleapp.web/src/app/app.module.ts",
        "sampleapp.web/src/assets/.gitkeep",
        "sampleapp.web/src/environments/environment.ts",
        "sampleapp.web/src/environments/environment.prod.ts",
        "sampleapp.web/src/favicon.ico",
        "sampleapp.web/src/index.html",
        "sampleapp.web/src/main.ts",
        "sampleapp.web/src/polyfills.ts",
        "sampleapp.web/src/styles.css",
        "sampleapp.web/src/test.ts",
        "sampleapp.web/.editorconfig",
        "sampleapp.web/.gitignore",
        "sampleapp.web/angular.json",
        "sampleapp.web/browserslist",
        "sampleapp.web/karma.conf.js",
        "sampleapp.web/package.json",
        "sampleapp.web/package-lock.json",
        "sampleapp.web/README.md",
        "sampleapp.web/tsconfig.json",
        "sampleapp.web/tsconfig.app.json",
        "sampleapp.web/tsconfig.spec.json",
        "sampleapp.web/tslint.json",
        "runway.yml",
    ]

    repo = cd_tmp_path / "static-angular"
    assert repo.is_dir()

    for file_ in files:
        assert (repo / file_).is_file()

    assert caplog.messages == [
        f"Sample static Angular site repo created at {repo}",
        "See the README for setup and deployment instructions.",
    ]


def test_static_react(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway gen-sample static-react`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", "static-react"])
    assert result.exit_code == 0

    files = [
        "sampleapp.web/public/favicon.ico",
        "sampleapp.web/public/index.html",
        "sampleapp.web/public/logo192.png",
        "sampleapp.web/public/logo512.png",
        "sampleapp.web/public/manifest.json",
        "sampleapp.web/public/robots.txt",
        "sampleapp.web/src/App.css",
        "sampleapp.web/src/App.js",
        "sampleapp.web/src/App.test.js",
        "sampleapp.web/src/index.css",
        "sampleapp.web/src/index.js",
        "sampleapp.web/src/logo.svg",
        "sampleapp.web/src/serviceWorker.js",
        "sampleapp.web/src/setupTests.js",
        "sampleapp.web/.gitignore",
        "sampleapp.web/package.json",
        "sampleapp.web/README.md",
        "runway.yml",
    ]

    repo = cd_tmp_path / "static-react"
    assert repo.is_dir()

    for file_ in files:
        assert (repo / file_).is_file()

    assert caplog.messages == [
        f"Sample static React site repo created at {repo}",
        "See the README for setup and deployment instructions.",
    ]


def test_tf(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway gen-sample tf`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", "tf"])
    assert result.exit_code == 0

    files = [
        ".terraform-version",
        "backend-us-east-1.tfvars",
        "dev-us-east-1.tfvars",
        "main.tf",
    ]

    module = cd_tmp_path / "sampleapp.tf"
    assert module.is_dir()

    for file_ in files:
        assert (module / file_).is_file()

    assert caplog.messages == [f"Sample Terraform app created at {module}"]


@pytest.mark.parametrize(
    "command, dir_name",
    [
        ("cdk-csharp", "sampleapp.cdk"),
        ("cdk-py", "sampleapp.cdk"),
        ("cdk-tsc", "sampleapp.cdk"),
        ("cfn", "sampleapp.cfn"),
        ("cfngin", "sampleapp.cfn"),
        ("sls-py", "sampleapp.sls"),
        ("sls-tsc", "sampleapp.sls"),
        ("static-angular", "static-angular"),
        ("static-react", "static-react"),
        ("tf", "sampleapp.tf"),
    ],
)
def test_dir_exists(
    command: str, dir_name: str, caplog: pytest.LogCaptureFixture, cd_tmp_path: Path
) -> None:
    """Test ``runway gen-sample`` commands when directory exists."""
    caplog.set_level(logging.ERROR, logger="runway.cli.gen_sample")
    dir_path = cd_tmp_path / dir_name
    dir_path.mkdir()

    runner = CliRunner()
    result = runner.invoke(cli, ["gen-sample", command])

    assert result.exit_code == 1
    assert caplog.messages == [f"Directory {dir_path} already exists!"]
