"""Serverless module."""
from __future__ import print_function

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

import yaml

from runway.hooks.staticsite.util import get_hash_of_files

from .._logging import PrefixAdaptor
from ..s3_util import does_s3_object_exist, download, ensure_bucket_exists, upload
from ..util import YamlDumper, cached_property, merge_dicts
from . import ModuleOptions, RunwayModuleNpm, generate_node_command, run_module_command

LOGGER = logging.getLogger(__name__)


def gen_sls_config_files(stage, region):
    """Generate possible SLS config files names."""
    names = []
    for ext in ["yml", "json"]:
        # Give preference to explicit stage-region files
        names.append(os.path.join("env", "%s-%s.%s" % (stage, region, ext)))
        names.append("config-%s-%s.%s" % (stage, region, ext))
        # Fallback to stage name only
        names.append(os.path.join("env", "%s.%s" % (stage, ext)))
        names.append("config-%s.%s" % (stage, ext))
    return names


def run_sls_print(sls_opts, env_vars, path):
    """Run sls print command."""
    sls_info_opts = list(sls_opts)
    sls_info_opts[0] = "print"
    sls_info_opts.extend(["--format", "yaml"])
    sls_info_cmd = generate_node_command(
        command="sls", command_opts=sls_info_opts, path=path
    )
    return yaml.safe_load(subprocess.check_output(sls_info_cmd, env=env_vars))


def get_src_hash(sls_config, path):
    """Get hash(es) of serverless source."""
    funcs = sls_config["functions"]

    if sls_config.get("package", {}).get("individually"):
        hashes = {
            key: get_hash_of_files(
                os.path.join(path, os.path.dirname(funcs[key].get("handler")))
            )
            for key in funcs.keys()
        }
    else:
        directories = []
        for (key, value) in funcs.items():
            func_path = {"path": os.path.dirname(value.get("handler"))}
            if func_path not in directories:
                directories.append(func_path)
        hashes = {sls_config["service"]: get_hash_of_files(path, directories)}

    return hashes


def deploy_package(sls_opts, bucketname, context, path, logger=LOGGER):
    """Run sls package command.

    Args:
        sls_opts (List[str]): List of options for Serverless CLI.
        bucketname (str): S3 Bucket name.
        context (Context): Runway context object.
        path (str): Module path.
        logger(Optional[logging.Logger]): A more granular
            logger for log messages.

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

    logger.info("package %s (in progress)", os.path.basename(path))
    run_module_command(
        cmd_list=sls_package_cmd, env_vars=context.env.vars, logger=logger
    )
    logger.info("package %s (complete)", os.path.basename(path))

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

    def __init__(self, context, path, options=None):
        """Instantiate class.

        Args:
            context (Context): Runway context object.
            path (str): Path to the module.
            options (Dict[str, Dict[str, Any]]): Everything in the module
                definition merged with applicable values from the deployment
                definition.

        """
        options = options or {}
        super(Serverless, self).__init__(context, path, options.copy())
        self.logger = PrefixAdaptor(self.name, LOGGER)
        try:
            self.options = ServerlessOptions.parse(**options.get("options", {}))
        except ValueError:
            self.logger.exception("error encountered while parsing options")
            sys.exit(1)
        self.region = self.context.env.aws_region
        self.stage = self.context.env.name

    @property
    def cli_args(self):
        """Generate CLI args from self used in all Serverless commands.

        Returns:
            List[str]

        """
        result = ["--region", self.region, "--stage", self.stage]
        if "DEBUG" in self.context.env.vars:
            result.append("--verbose")
        return result

    @cached_property
    def env_file(self):
        """Find the environment file for the module.

        Returns:
            Path: Path object for the environment file that was found.

        """
        for name in gen_sls_config_files(self.stage, self.region):
            test_path = self.path / name
            if test_path.is_file():
                return test_path
        return None

    @property
    def skip(self):
        """Determine if the module should be skipped.

        Returns:
            bool: To skip, or not to skip, that is the question.

        """
        if not self.package_json_missing():
            if self.parameters or self.environments or self.env_file:
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

    def extend_serverless_yml(self, func):
        """Extend the Serverless config file with additional YAML from options.

        Args:
            func (Callable): Callable to use after handling the Serverless
                config file.

        """
        self.npm_install()  # doing this here for a cleaner log
        self.logger.info("extending Serverless config from runway.yml...")
        final_yml = merge_dicts(
            self.sls_print(skip_install=True), self.options.extend_serverless_yml
        )
        # using a unique name to prevent collisions when run in parallel
        tmp_file = self.path / "{}.tmp.serverless.yml".format(uuid.uuid4())

        try:
            if self.context.is_python3:
                tmp_file.write_text(yaml.safe_dump(final_yml))
            else:  # TODO remove handling when dropping python 2 support
                tmp_file.write_text(yaml.safe_dump(final_yml).decode("UTF-8"))
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

    def gen_cmd(self, command, args_list=None):
        """Generate and log a Serverless command.

        This does not execute the command, only prepares it for use.

        Args:
            command (str): The Serverless command to be executed.
            args_list (Optiona[List[str]]): Additional arguments to include
                in the generated command.

        Returns:
            List[str]: The full command to be passed into a subprocess.

        """
        args = [command] + self.cli_args + self.options.args
        args.extend(args_list or [])
        if self.context.no_color and "--no-color" not in args:
            args.append("--no-color")
        if command not in ["remove", "print"] and self.context.is_noninteractive:
            args.append("--conceal")  # hide secrets from serverless output
        return generate_node_command(
            command="sls", command_opts=args, path=self.path, logger=self.logger
        )

    def sls_deploy(self, skip_install=False):
        """Execute ``sls deploy`` command.

        Args:
            skip_install (bool): Skip ``npm install`` before running the
                Serverless command. (*default:* ``False``)

        """
        if not skip_install:
            self.npm_install()

        if self.options.promotezip:
            # TODO refactor deploy_package to be part of the class
            self.path.absolute()
            sls_opts = ["deploy"] + self.cli_args + self.options.args
            if self.context.no_color and "--no-color" not in sls_opts:
                sls_opts.append("--no-color")
            deploy_package(
                sls_opts,
                self.options.promotezip["bucketname"],
                self.context,
                str(self.path),
                self.logger,
            )
            return
        self.logger.info("deploy (in progress)")
        run_module_command(
            cmd_list=self.gen_cmd("deploy"),
            env_vars=self.context.env.vars,
            logger=self.logger,
        )
        self.logger.info("deploy (complete)")

    def sls_print(self, item_path=None, skip_install=False):
        """Execute ``sls print`` command.

        Keyword Args:
            item_path (Optional[str]): Period-separated path to print a
                sub-value (eg: "provider.name").
            skip_install (bool): Skip ``npm install`` before running the
                Serverless command. (*default:* ``False``)

        Returns:
            Dict[str, Any]: Resolved Serverless config file.

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
                self.gen_cmd("print", args_list=args), env=self.context.env.vars
            )
        )
        # this could be expensive so only dump if needed
        if self.logger.getEffectiveLevel() == logging.DEBUG:
            self.logger.debug(
                "resolved Serverless config:\n%s", yaml.dump(result, Dumper=YamlDumper)
            )
        return result

    def sls_remove(self, skip_install=False):
        """Execute ``sls remove`` command.

        Args:
            skip_install (bool): Skip ``npm install`` before running the
                Serverless command. (*default:* ``False``)

        """
        if not skip_install:
            self.npm_install()
        stack_missing = False  # track output for acceptable error
        self.logger.info("destroy (in progress)")
        proc = subprocess.Popen(
            self.gen_cmd("remove"),
            bufsize=1,
            env=self.context.env.vars,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        with proc.stdout:  # live output
            for line in proc.stdout:
                print(line, end="")
                if re.search(r"Stack '.*' does not exist", line):
                    stack_missing = True
        if proc.wait() != 0 and not stack_missing:
            sys.exit(proc.returncode)
        self.logger.info("destroy (complete)")

    def plan(self):
        """Entrypoint for Runway's plan action."""
        self.logger.info("plan not currently supported for Serverless")

    def deploy(self):
        """Entrypoint for Runway's deploy action."""
        if self.skip:
            return
        if self.options.extend_serverless_yml:
            self.extend_serverless_yml(self.sls_deploy)
        else:
            self.sls_deploy()

    def destroy(self):
        """Entrypoint for Runway's destroy action."""
        if self.skip:
            return
        if self.options.extend_serverless_yml:
            self.extend_serverless_yml(self.sls_remove)
        else:
            self.sls_remove()


class ServerlessOptions(ModuleOptions):
    """Module options for Serverless."""

    def __init__(self, args, extend_serverless_yml, promotezip, skip_npm_ci=False):
        """Instantiate class.

        Keyword Args:
            args (List[str]): Arguments to append to Serverless CLI
                commands. These will always be placed after the default
                arguments provided by Runway.
            extend_serverless_yml (Dict[str, Any]): If provided,
                a temporary Serverless config will be created will be created
                from what exists in the module directory then the value of
                this option will be merged into it. The temporary file will
                be deleted at the end of execution.
            promotezip (Dict[str, str]): If provided, promote
                Serverless generated zip files between environments from a
                *build* AWS account.
            skip_npm_ci (bool): Skip the ``npm ci`` Runway executes at the
                begining of each Serverless module run.

        """
        super(ServerlessOptions, self).__init__()
        self._arg_parser = self._create_arg_parser()
        self.extend_serverless_yml = extend_serverless_yml
        cli_args, self._unknown_cli_args = self._arg_parser.parse_known_args(
            list(args) if isinstance(args, list) else []  # python 2 compatible
        )
        self._cli_args = vars(cli_args)  # convert argparse.Namespace to dict
        self.promotezip = promotezip
        self.skip_npm_ci = skip_npm_ci

    @property
    def args(self):
        """Args to pass to the CLI.

        Returns:
            List[str]: List of arguments.

        """
        known_args = []
        for key, val in self._cli_args.items():
            if isinstance(val, str):
                known_args.extend(["--%s" % key, val])
        return known_args + self._unknown_cli_args

    def update_args(self, key, value):
        """Update a known CLI argument.

        Args:
            key (str): Dict key to be updated.
            value (str): New value

        Raises:
            KeyError: The key provided for update is now a known arg.

        """
        if key in self._cli_args:
            self._cli_args[key] = value
        else:
            raise KeyError(key)

    @staticmethod
    def _create_arg_parser():
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
    def parse(cls, **kwargs):  # pylint: disable=arguments-differ
        """Parse the options definition and return an options object.

        Keyword Args:
            args (Optional[List[str]]): Arguments to append to Serverless CLI
                commands. These will always be placed after the default
                arguments provided by Runway.
            extend_serverless_yml (Optional[Dict[str, Any]]): If provided,
                a temporary Serverless config will be created will be created
                from what exists in the module directory then the value of
                this option will be merged into it. The temporary file will
                be deleted at the end of execution.
            promotezip (Optional[Dict[str, str]]): If provided, promote
                Serverless generated zip files between environments from a
                *build* AWS account.
            skip_npm_ci (bool): Skip the ``npm ci`` Runway executes at the
                begining of each Serverless module run.

        Returns:
            ServerlessOptions

        Raises:
            ValueError: promotezip was provided but missing bucketname.

        """
        promotezip = kwargs.get("promotezip", {})
        if promotezip and not promotezip.get("bucketname"):
            raise ValueError(
                '"bucketname" must be provided when using '
                '"options.promotezip": {}'.format(promotezip)
            )
        return cls(
            args=kwargs.get("args", []),
            extend_serverless_yml=kwargs.get("extend_serverless_yml", {}),
            promotezip=promotezip,
            skip_npm_ci=kwargs.get("skip_npm_ci", False),
        )
