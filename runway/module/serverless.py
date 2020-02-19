"""Serverless module."""
from __future__ import print_function

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import yaml

from runway.hooks.staticsite.util import get_hash_of_files
from . import (
    RunwayModule, format_npm_command_for_logging, generate_node_command,
    run_module_command, run_npm_install, warn_on_boto_env_vars
)
from ..util import change_dir, which
from ..s3_util import ensure_bucket_exists, does_s3_object_exist, download, upload

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

def deploy_package(sls_opts, options, context, path): # noqa pylint: disable=too-many-locals
    """Run sls package command."""
    bucketname = options.get('options', {}).get('promotezip', {}).get('bucketname', {})
    if not bucketname:
        raise ValueError('"bucketname" must be specified when using "promotezip"')

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
        sls_opts.extend(self.options.get('options', {}).get('args', []))

        sls_cmd = generate_node_command(command='sls',
                                        command_opts=sls_opts,
                                        path=self.path)

        if (
                self.options['parameters'] or
                os.path.isfile(os.path.join(self.path, sls_env_file))
        ):
            if os.path.isfile(os.path.join(self.path, 'package.json')):
                with change_dir(self.path):
                    run_npm_install(self.path, self.options, self.context)
                    if command == 'deploy' and self.options.get('options', {}).get('promotezip', {}): # noqa pylint: disable=line-too-long
                        deploy_package(sls_opts,
                                       self.options,
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
