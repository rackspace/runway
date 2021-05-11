"""Serverless module."""
from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from typing import IO, TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union, cast

import yaml

from .._logging import PrefixAdaptor
from ..cfngin.hooks.staticsite.utils import get_hash_of_files
from ..compat import cached_property
from ..config.models.runway.options.serverless import (
    RunwayServerlessModuleOptionsDataModel,
)
from ..s3_utils import does_s3_object_exist, download, ensure_bucket_exists, upload
from ..utils import YamlDumper, merge_dicts
from .base import ModuleOptions, RunwayModuleNpm
from .utils import generate_node_command, run_module_command

if TYPE_CHECKING:
    from pathlib import Path

    from .._logging import RunwayLogger
    from ..context import RunwayContext

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


def gen_sls_config_files(stage: str, region: str) -> List[str]:
    """Generate possible SLS config files names."""
    names: List[str] = []
    for ext in ["yml", "json"]:
        # Give preference to explicit stage-region files
        names.append(os.path.join("env", "%s-%s.%s" % (stage, region, ext)))
        names.append("config-%s-%s.%s" % (stage, region, ext))
        # Fallback to stage name only
        names.append(os.path.join("env", "%s.%s" % (stage, ext)))
        names.append("config-%s.%s" % (stage, ext))
    return names


def run_sls_print(
    sls_opts: List[str], env_vars: Dict[str, str], path: Path
) -> Dict[str, Any]:
    """Run sls print command."""
    sls_info_opts = list(sls_opts)
    sls_info_opts[0] = "print"
    sls_info_opts.extend(["--format", "yaml"])
    sls_info_cmd = generate_node_command(
        command="sls", command_opts=sls_info_opts, path=path
    )
    return yaml.safe_load(
        subprocess.check_output(
            sls_info_cmd, env={"SLS_DEPRECATION_DISABLE": "*", **env_vars}
        )
    )


def get_src_hash(sls_config: Dict[str, Any], path: Path) -> Dict[str, str]:
    """Get hash(es) of serverless source."""
    funcs = sls_config["functions"]

    if sls_config.get("package", {"": ""}).get("individually"):
        return {
            key: get_hash_of_files(path / os.path.dirname(funcs[key].get("handler")))
            for key in funcs.keys()
        }
    directories: List[Dict[str, Union[List[str], str]]] = []
    for _key, value in funcs.items():
        func_path = {"path": os.path.dirname(value.get("handler"))}
        if func_path not in directories:
            directories.append(func_path)
    if isinstance(sls_config["service"], dict):
        # handle sls<3.0.0 potential service property object notation
        return {sls_config["service"]["name"]: get_hash_of_files(path, directories)}
    return {sls_config["service"]: get_hash_of_files(path, directories)}


def deploy_package(
    sls_opts: List[str],
    bucketname: str,
    context: RunwayContext,
    path: Path,
    logger: Union[logging.Logger, logging.LoggerAdapter] = LOGGER,
) -> None:
    """Run sls package command.

    Args:
        sls_opts: List of options for Serverless CLI.
        bucketname: S3 Bucket name.
        context: Runway context object.
        path: Module path.
        logger: A more granular logger for log messages.

    """
    package_dir = tempfile.mkdtemp()
    logger.debug("package directory: %s", package_dir)

    ensure_bucket_exists(bucketname, context.env.aws_region)
    sls_config = run_sls_print(sls_opts, context.env.vars, path)
    hashes = get_src_hash(sls_config, path)

    sls_opts[0] = "package"
    sls_opts.extend(["--package", package_dir])
    sls_package_cmd = generate_node_command(
        command="sls", command_opts=sls_opts, path=path
    )

    logger.info("package %s (in progress)", path.name)
    run_module_command(
        cmd_list=sls_package_cmd, env_vars=context.env.vars, logger=logger
    )
    logger.info("package %s (complete)", path.name)

    for key in hashes.keys():
        hash_zip = hashes[key] + ".zip"
        func_zip = os.path.basename(key) + ".zip"
        if does_s3_object_exist(bucketname, hash_zip):
            logger.info("found existing package for %s", key)
            download(bucketname, hash_zip, os.path.join(package_dir, func_zip))
        else:
            logger.info("no existing package found for %s", key)
            zip_name = os.path.join(package_dir, func_zip)
            upload(bucketname, hash_zip, zip_name)

    sls_opts[0] = "deploy"
    # --package must be provided to "deploy" as a relative path to support
    # serverless@<1.70.0. the fix to support absolute path was implimented
    # somewhere between 1.60.0 and 1.70.0.
    sls_opts[-1] = os.path.relpath(package_dir)
    sls_deploy_cmd = generate_node_command(
        command="sls", command_opts=sls_opts, path=path
    )

    logger.info("deploy (in progress)")
    run_module_command(
        cmd_list=sls_deploy_cmd, env_vars=context.env.vars, logger=logger
    )
    logger.info("deploy (complete)")

    shutil.rmtree(package_dir)


class Serverless(RunwayModuleNpm):
    """Serverless Runway Module."""

    options: ServerlessOptions

    def __init__(
        self,
        context: RunwayContext,
        *,
        explicitly_enabled: Optional[bool] = False,
        logger: RunwayLogger = LOGGER,
        module_root: Path,
        name: Optional[str] = None,
        options: Optional[Union[Dict[str, Any], ModuleOptions]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> None:
        """Instantiate class.

        Args:
            context: Runway context object for the current session.
            explicitly_enabled: Whether or not the module is explicitly enabled.
                This is can be set in the event that the current environment being
                deployed to matches the defined environments of the module/deployment.
            logger: Used to write logs.
            module_root: Root path of the module.
            name: Name of the module.
            options: Options passed to the module class from the config as ``options``
                or ``module_options`` if coming from the deployment level.
            parameters: Values to pass to the underlying infrastructure as code
                tool that will alter the resulting infrastructure being deployed.
                Used to templatize IaC.

        """
        super().__init__(
            context,
            explicitly_enabled=explicitly_enabled,
            logger=logger,
            module_root=module_root,
            name=name,
            options=ServerlessOptions.parse_obj(options or {}),
            parameters=parameters,
        )
        self.logger = PrefixAdaptor(self.name, logger)
        self.stage = self.ctx.env.name

    @property
    def cli_args(self) -> List[str]:
        """Generate CLI args from self used in all Serverless commands."""
        result = ["--region", self.region, "--stage", self.stage]
        if "DEBUG" in self.ctx.env.vars:
            result.append("--verbose")
        return result

    @cached_property
    def env_file(self) -> Optional[Path]:
        """Find the environment file for the module."""
        for name in gen_sls_config_files(self.stage, self.region):
            test_path = self.path / name
            if test_path.is_file():
                return test_path
        return None

    @property
    def skip(self) -> bool:
        """Determine if the module should be skipped."""
        if not self.package_json_missing():
            if self.parameters or self.explicitly_enabled or self.env_file:
                return False
            self.logger.info(
                "skipped; config file for this stage/region not found"
                " -- looking for one of: %s",
                ", ".join(gen_sls_config_files(self.stage, self.region)),
            )
        else:
            self.logger.info(
                'skipped; package.json with "serverless" in devDependencies'
                " is required for this module type"
            )
        return True

    def extend_serverless_yml(self, func: Callable[..., None]) -> None:
        """Extend the Serverless config file with additional YAML from options.

        Args:
            func: Callable to use after handling the Serverless config file.

        """
        self.npm_install()  # doing this here for a cleaner log
        self.logger.info("extending Serverless config from runway.yml...")
        final_yml = merge_dicts(
            self.sls_print(skip_install=True), self.options.extend_serverless_yml
        )
        # using a unique name to prevent collisions when run in parallel
        tmp_file = self.path / "{}.tmp.serverless.yml".format(uuid.uuid4())

        try:
            tmp_file.write_text(yaml.safe_dump(final_yml))
            self.logger.debug("created temporary Serverless config: %s", tmp_file)
            self.options.update_args("config", str(tmp_file.name))
            self.logger.debug(
                "updated options.args with temporary Serverless config: %s",
                tmp_file.name,
            )
            func(skip_install=True)
        finally:
            try:
                tmp_file.unlink()  # always cleanup the temp file
                self.logger.debug("removed temporary Serverless config")
            except OSError:
                self.logger.debug(
                    "encountered an error when trying to delete the "
                    "temporary Serverless config",
                    exc_info=True,
                )

    def gen_cmd(self, command: str, args_list: Optional[List[str]] = None) -> List[str]:
        """Generate and log a Serverless command.

        This does not execute the command, only prepares it for use.

        Args:
            command: The Serverless command to be executed.
            args_list: Additional arguments to include in the generated command.

        Returns:
            The full command to be passed into a subprocess.

        """
        args = [command] + self.cli_args + self.options.args
        args.extend(args_list or [])
        if self.ctx.no_color and "--no-color" not in args:
            args.append("--no-color")
        if command not in ["remove", "print"] and self.ctx.is_noninteractive:
            args.append("--conceal")  # hide secrets from serverless output
        return generate_node_command(
            command="sls", command_opts=args, path=self.path, logger=self.logger
        )

    def sls_deploy(self, skip_install: bool = False) -> None:
        """Execute ``sls deploy`` command.

        Args:
            skip_install: Skip ``npm install`` before running the
                Serverless command. (*default:* ``False``)

        """
        if not skip_install:
            self.npm_install()

        if self.options.promotezip:
            # TODO refactor deploy_package to be part of the class
            self.path.absolute()
            sls_opts = ["deploy"] + self.cli_args + self.options.args
            if self.ctx.no_color and "--no-color" not in sls_opts:
                sls_opts.append("--no-color")
            deploy_package(
                sls_opts,
                self.options.promotezip["bucketname"],
                self.ctx,
                self.path,
                self.logger,
            )
            return
        self.logger.info("deploy (in progress)")
        run_module_command(
            cmd_list=self.gen_cmd("deploy"),
            env_vars=self.ctx.env.vars,
            logger=self.logger,
        )
        self.logger.info("deploy (complete)")

    def sls_print(
        self, item_path: Optional[str] = None, skip_install: bool = False
    ) -> Dict[str, Any]:
        """Execute ``sls print`` command.

        Keyword Args:
            item_path: Period-separated path to print a sub-value (eg: "provider.name").
            skip_install: Skip ``npm install`` before running the Serverless command.
                (*default:* ``False``)

        Returns:
            Resolved Serverless config file.

        Raises:
            SystemExit: If a runway-tmp.serverless.yml file already exists.

        """
        if not skip_install:
            self.npm_install()

        args = ["--format", "yaml"]
        if item_path:
            args.extend(["--path", item_path])
        result = yaml.safe_load(
            subprocess.check_output(
                self.gen_cmd("print", args_list=args),
                # disable all deprecation messages to ensure the output is "clean"
                env={"SLS_DEPRECATION_DISABLE": "*", **self.ctx.env.vars},
            )
        )
        # this could be expensive so only dump if needed
        if self.logger.getEffectiveLevel() == logging.DEBUG:
            self.logger.debug(  # cov: ignore
                "resolved Serverless config:\n%s", yaml.dump(result, Dumper=YamlDumper)
            )
        return result

    def sls_remove(self, skip_install: bool = False) -> None:
        """Execute ``sls remove`` command.

        Args:
            skip_install: Skip ``npm install`` before running the Serverless command.
                (*default:* ``False``)

        """
        if not skip_install:
            self.npm_install()
        stack_missing = False  # track output for acceptable error
        self.logger.info("destroy (in progress)")
        with subprocess.Popen(
            self.gen_cmd("remove"),
            bufsize=1,
            env=self.ctx.env.vars,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        ) as proc:
            with cast(IO[str], proc.stdout):
                for line in cast(IO[str], proc.stdout):
                    print(line, end="")
                    if re.search(r"Stack '.*' does not exist", line):
                        stack_missing = True
        if proc.wait() != 0 and not stack_missing:
            sys.exit(proc.returncode)
        self.logger.info("destroy (complete)")

    def plan(self) -> None:
        """Entrypoint for Runway's plan action."""
        self.logger.info("plan not currently supported for Serverless")

    def deploy(self) -> None:
        """Entrypoint for Runway's deploy action."""
        if self.skip:
            return
        if self.options.extend_serverless_yml:
            self.extend_serverless_yml(self.sls_deploy)
        else:
            self.sls_deploy()

    def destroy(self) -> None:
        """Entrypoint for Runway's destroy action."""
        if self.skip:
            return
        if self.options.extend_serverless_yml:
            self.extend_serverless_yml(self.sls_remove)
        else:
            self.sls_remove()


class ServerlessOptions(ModuleOptions):
    """Module options for Serverless Framework.

    Attributes:
        data: Options parsed into a data model.
        extend_serverless_yml: If provided, the value of this option will be
            recursively merged into the module's Serverless config file.
        promotezip: If provided, promote Serverless Framework generated zip files
            between environments from a build AWS account.
        skip_npm_ci: Skip running ``npm ci`` in the module directory prior to
            processing the module.

    """

    def __init__(self, data: RunwayServerlessModuleOptionsDataModel) -> None:
        """Instantiate class.

        Args:
            data: Options parsed into a data model.

        """
        self._arg_parser = self._create_arg_parser()
        cli_args, self._unknown_cli_args = self._arg_parser.parse_known_args(
            data.args.copy()
        )
        self._cli_args = vars(cli_args)  # convert argparse.Namespace to dict

        self.data = data
        self.extend_serverless_yml = data.extend_serverless_yml
        self.promotezip = data.promotezip
        self.skip_npm_ci = data.skip_npm_ci

    @property
    def args(self) -> List[str]:
        """List of CLI arguments/options to pass to the Serverless Framework CLI."""
        known_args: List[str] = []
        for key, val in self._cli_args.items():
            if isinstance(val, str):
                known_args.extend(["--%s" % key, val])
        return known_args + self._unknown_cli_args

    def update_args(self, key: str, value: str) -> None:
        """Update a known CLI argument.

        Args:
            key: Dict key to be updated.
            value: New value

        Raises:
            KeyError: The key provided for update is not a known arg.

        """
        if key in self._cli_args:
            self._cli_args[key] = value
        else:
            raise KeyError(key)

    @staticmethod
    def _create_arg_parser() -> argparse.ArgumentParser:
        """Create argparse parser to parse args.

        Used to pull arguments out of self.args when logic could change
        depending on values provided.

        Returns:
            argparse.ArgumentParser

        """
        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--config", default=None)
        return parser

    @classmethod
    def parse_obj(cls, obj: object) -> ServerlessOptions:
        """Parse options definition and return an options object.

        Args:
            obj: Object to parse.

        """
        return cls(data=RunwayServerlessModuleOptionsDataModel.parse_obj(obj))
