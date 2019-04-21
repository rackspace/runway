"""Serverless module."""
from __future__ import print_function

import logging
import os
import re
import subprocess
import sys

from . import (
    RunwayModule, format_npm_command_for_logging, generate_node_command,
    run_module_command, run_npm_install, warn_on_boto_env_vars
)
from ..util import change_dir, which

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
    print(stdoutdata)
    if sls_return != 0 and (sls_return == 1 and not (
            re.search(r"Stack '.*' does not exist", stdoutdata))):
        sys.exit(sls_return)


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

        sls_cmd = generate_node_command(command='sls',
                                        command_opts=sls_opts,
                                        path=self.path)

        if (not self.options.get('environments') and os.path.isfile(os.path.join(self.path, sls_env_file))) or (  # noqa pylint: disable=line-too-long
                self.options.get('environments', {}).get(self.context.env_name)):  # noqa
            if os.path.isfile(os.path.join(self.path, 'package.json')):
                with change_dir(self.path):
                    run_npm_install(self.path, self.options, self.context)
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
