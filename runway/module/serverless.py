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

import yaml

from runway.hooks.staticsite.util import get_hash_of_files

from ..s3_util import (does_s3_object_exist, download, ensure_bucket_exists,
                       upload)
from ..util import change_dir, which
from . import (ModuleOptions, RunwayModule, format_npm_command_for_logging,
               generate_node_command, run_module_command, run_npm_install,
               warn_on_boto_env_vars)

if sys.version_info[0] > 2:  # TODO remove after droping python 2
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger('runway')


def gen_sls_config_files(stage, region):
    """Generate possible SLS config files names."""
    names = []
    for ext in ['yml', 'json']:
        # Give preference to explicit stage-region files
        names.append(
            os.path.join('env',
                         "%s-%s.%s" % (stage, region, ext))
        )
        names.append("config-%s-%s.%s" % (stage, region, ext))
        # Fallback to stage name only
        names.append(
            os.path.join('env',
                         "%s.%s" % (stage, ext))
        )
        names.append("config-%s.%s" % (stage, ext))
    return names


def get_sls_config_file(path, stage, region):
    """Determine Serverless config file name."""
    for name in gen_sls_config_files(stage, region):
        if os.path.isfile(os.path.join(path, name)):
            return name
    return "config-%s.json" % stage  # fallback to generic json name


def run_sls_remove(sls_cmd, env_vars):
    """Run sls remove command."""
    sls_process = subprocess.Popen(sls_cmd,
                                   stdout=subprocess.PIPE,
                                   env=env_vars)
    stdoutdata, _stderrdata = sls_process.communicate()
    sls_return = sls_process.wait()
    if int(sys.version[0]) > 2:
        stdoutdata = stdoutdata.decode('UTF-8')  # bytes -> string
    print(stdoutdata)
    if sls_return != 0 and (sls_return == 1 and not (
            re.search(r"Stack '.*' does not exist", stdoutdata))):
        sys.exit(sls_return)


def run_sls_print(sls_opts, env_vars, path):
    """Run sls print command."""
    sls_info_opts = sls_opts
    sls_info_opts[0] = 'print'
    sls_info_opts.extend(['--format', 'yaml'])
    sls_info_cmd = generate_node_command(command='sls',
                                         command_opts=sls_info_opts,
                                         path=path)
    return yaml.safe_load(subprocess.check_output(sls_info_cmd,
                                                  env=env_vars))


def get_src_hash(sls_config, path):
    """Get hash(es) of serverless source."""
    funcs = sls_config['functions']

    if sls_config.get('package', {}).get('individually'):
        hashes = {key: get_hash_of_files(os.path.join(path,
                                                      os.path.dirname(funcs[key].get('handler'))))
                  for key in funcs.keys()}
    else:
        directories = []
        for (key, value) in funcs.items():
            func_path = {'path': os.path.dirname(value.get('handler'))}
            if func_path not in directories:
                directories.append(func_path)
        hashes = {sls_config['service']: get_hash_of_files(path, directories)}

    return hashes


def deploy_package(sls_opts, bucketname, context, path):
    """Run sls package command."""
    package_dir = tempfile.mkdtemp()
    LOGGER.debug('Package directory: %s', package_dir)

    ensure_bucket_exists(bucketname, context.env_region)
    sls_config = run_sls_print(sls_opts, context.env_vars, path)
    hashes = get_src_hash(sls_config, path)

    sls_opts[0] = 'package'
    sls_opts.extend(['--package', os.path.relpath(package_dir,
                                                  path)])
    sls_package_cmd = generate_node_command(command='sls',
                                            command_opts=sls_opts,
                                            path=path)

    LOGGER.info("Running sls package on %s (\"%s\")",
                os.path.basename(path),
                format_npm_command_for_logging(sls_package_cmd))

    run_module_command(cmd_list=sls_package_cmd,
                       env_vars=context.env_vars)

    for key in hashes.keys():
        hash_zip = hashes[key] + ".zip"
        func_zip = os.path.basename(key) + ".zip"
        if does_s3_object_exist(bucketname, hash_zip):
            LOGGER.info('Found existing package "s3://%s/%s" for %s', bucketname, hash_zip, key)
            download(bucketname, hash_zip, os.path.join(package_dir, func_zip))
        else:
            LOGGER.info('No existing package found, uploading to s3://%s/%s', bucketname,
                        hash_zip)
            zip_name = os.path.join(package_dir, func_zip)
            upload(bucketname, hash_zip, zip_name)

    sls_opts[0] = 'deploy'
    sls_deploy_cmd = generate_node_command(command='sls',
                                           command_opts=sls_opts,
                                           path=path)

    LOGGER.info("Running sls deploy on %s (\"%s\")",
                os.path.basename(path),
                format_npm_command_for_logging(sls_deploy_cmd))
    run_module_command(cmd_list=sls_deploy_cmd,
                       env_vars=context.env_vars)

    shutil.rmtree(package_dir)


class Serverless(RunwayModule):
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
        super(Serverless, self).__init__(context, path, options)
        del self.options  # remove the attr set by the parent class
        options.pop('path', None)  # this

        self._raw_path = options.pop('path', None)  # unresolved path
        self.environments = options.pop('environments', {})
        self.options = ServerlessOptions.parse(**options.pop('options', {}))
        self.parameters = options.pop('parameters', {})

        for k, v in options.items():
            setattr(self, k, v)

        LOGGER.warning(self.path)

    def run_cmd(self, command, *args, arg_list=None, exit_on_error=True):
        """Run a command with this modules underlying CLI.

        Args:
            command (str): The command to be executed with Serverless.

        Keyword Args:
            arg_list (Optional[List[str]]): List of arguments to include in
                the command.
            exit_on_error (bool): Perform sys.exit if the command fails.

        """
        args = list(args)
        args.extend(arg_list or [])
        args.insert(0, command)
        cmd = generate_node_command(command='sls',
                                    command_opts=args,
                                    path=self.path)
        run_module_command(cmd_list=cmd,
                           env_vars=self.context.env_vars,
                           exit_on_error=exit_on_error)

    def print(self, item_path=None, output_format='yaml'):
        """Print the Serverless file with all variables resolved.

        Keyword Args:
            item_path (Optional[str]): Period-separated path to print a
                sub-value (eg: "provider.name").
            output_format (str) Print configuration in given format
                ("yaml", "json", "text"). *(default: yaml)*

        Returns:
            Path: Path object for the output file.

        Raises:
            SystemExit: If a runway-tmp.serverless.yml file already exists.

        """
        args = ['print',
                '--region', self.context.env_region,
                '--stage', self.context.env_name,
                '--format', output_format]
        if item_path:
            args.extend(['--path', item_path])
        args.extend(self.options.args)

        output_file = Path(self.path) / 'runway-tmp.serverless.yml'
        if output_file.exists():
            LOGGER.error('Unable to save resolved Serverless file. '
                         'Runway temporary file already exists: %s',
                         output_file)
            sys.exit(1)

        with open(output_file, 'w') as file_:
            proc = subprocess.Popen(generate_node_command(command='sls',
                                                          command_opts=args,
                                                          path=self.path),
                                    cwd=self.path, stdout=file_,
                                    env=self.context.env_vars)
            if proc.wait() != 0:
                file_.close()
                output_file.unlink()
                sys.exit(proc.returncode)
        return output_file

    def run_serverless(self, command='deploy'):
        """Run Serverless."""
        response = {'skipped_configs': False}
        sls_opts = [command]

        if not which('npm'):
            LOGGER.error('"npm" not found in path or is not executable; '
                         'please ensure it is installed correctly.')
            sys.exit(1)

        if 'CI' in self.context.env_vars and command != 'remove':
            sls_opts.append('--conceal')  # Hide secrets from serverless output

        if 'DEBUG' in self.context.env_vars:
            sls_opts.append('-v')  # Increase logging if requested

        warn_on_boto_env_vars(self.context.env_vars)

        sls_opts.extend(['-r', self.context.env_region])
        sls_opts.extend(['--stage', self.context.env_name])
        sls_env_file = get_sls_config_file(self.path,
                                           self.context.env_name,
                                           self.context.env_region)
        sls_opts.extend(self.options.args)

        sls_cmd = generate_node_command(command='sls',
                                        command_opts=sls_opts,
                                        path=self.path)

        if (
                self.parameters or
                os.path.isfile(os.path.join(self.path, sls_env_file))
        ):
            if os.path.isfile(os.path.join(self.path, 'package.json')):
                with change_dir(self.path):
                    run_npm_install(self.path, {'options': self.options},
                                    self.context)
                    if command == 'deploy' and self.options.promotezip:
                        deploy_package(sls_opts,
                                       self.options.promotezip['bucketname'],
                                       self.context,
                                       self.path)
                        return response

                    LOGGER.info("Running sls %s on %s (\"%s\")",
                                command,
                                os.path.basename(self.path),
                                format_npm_command_for_logging(sls_cmd))
                    if command == 'remove':
                        # Need to account for exit code 1 on any removals after
                        # the first
                        run_sls_remove(sls_cmd, self.context.env_vars)
                    else:
                        run_module_command(cmd_list=sls_cmd,
                                           env_vars=self.context.env_vars)
            else:
                LOGGER.warning(
                    "Skipping serverless %s of %s; no \"package.json\" "
                    "file was found (need a package file specifying "
                    "serverless in devDependencies)",
                    command,
                    os.path.basename(self.path))
        else:
            response['skipped_configs'] = True
            LOGGER.info(
                "Skipping serverless %s of %s; no config file for "
                "this stage/region found (looking for one of \"%s\")",
                command,
                os.path.basename(self.path),
                ', '.join(gen_sls_config_files(self.context.env_name,
                                               self.context.env_region)))
        return response

    def plan(self):
        """Skip sls planning."""
        LOGGER.info('Planning not currently supported for Serverless')

    def deploy(self):
        """Run sls deploy."""
        self.run_serverless(command='deploy')

    def destroy(self):
        """Run serverless remove."""
        self.run_serverless(command='remove')


class ServerlessOptions(ModuleOptions):
    """Module options for Serverless."""

    def __init__(self, args=None, promotezip=None, skip_npm_ci=False):
        """Instantiate class.

        Keyword Args:
            args (Optional[List[str]]): Arguments to append to Serverless CLI
                commands. These will always be placed after the default
                arguments provided by Runway.
            promotezip (Optional[Dict[str, str]]): If provided, promote
                Serverless generated zip files between environments from a
                *build* AWS account.
            skip_npm_ci (bool): Skip the ``npm ci`` Runway executes at the
                begining of each Serverless module run.

        """
        super(ServerlessOptions, self).__init__()
        self._arg_parser = self._create_arg_parser()
        self.args = args or []
        self.cli_args, _ = self._arg_parser.parse_known_args(self.args)
        self.promotezip = promotezip or {}
        self.skip_npm_ci = skip_npm_ci

    @staticmethod
    def _create_arg_parser():
        """Create argparse parser to parse args.

        Used to pull arguments out of self.args when logic could change
        depending on values provided.

        Returns:
            argparse.ArgumentParser

        """
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', default=None)
        return parser

    @classmethod
    def parse(cls, **kwargs):  # pylint: disable=arguments-differ
        """Parse the options definition and return an options object.

        Keyword Args:
            args (Optional[List[str]]): Arguments to append to Serverless CLI
                commands. These will always be placed after the default
                arguments provided by Runway.
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
        promotezip = kwargs.get('promotezip')
        if promotezip and not promotezip.get('bucketname'):
            raise ValueError('"bucketname" must be specified when using '
                             '"promotezip": {}'.format(promotezip))
        return cls(args=kwargs.get('args'),
                   promotezip=promotezip,
                   skip_npm_ci=kwargs.get('skip_npm_ci', False))
