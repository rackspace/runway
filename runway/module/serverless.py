"""Terraform module."""

import logging
import os
import subprocess
import sys

from . import RunwayModule, run_module_command, warn_on_skipped_configs
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


def use_npm_ci(path):
    """Return true if npm ci should be used in lieu of npm install."""
    # https://docs.npmjs.com/cli/ci#description
    with open(os.devnull, 'w') as fnull:
        if ((os.path.isfile(os.path.join(path,
                                         'package-lock.json')) or
             os.path.isfile(os.path.join(path,
                                         'npm-shrinkwrap.json'))) and
                subprocess.call(
                    ['npm', 'ci', '-h'],
                    stdout=fnull,
                    stderr=subprocess.STDOUT
                ) == 0):
            return True
    return False


class Serverless(RunwayModule):
    """Terraform Serverless Module."""

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

        sls_opts.extend(['-r', self.context.env_region])
        sls_opts.extend(['--stage', self.context.env_name])
        sls_env_file = get_sls_config_file(self.path,
                                           self.context.env_name,
                                           self.context.env_region)

        if which('npx'):
            # Use npx if available (npm v5.2+)
            LOGGER.debug('Using npx to invoke sls.')
            # The nested sls-through-npx-via-subprocess command invocation
            # requires this redundant quoting
            sls_cmd = ['npx', '-c', "''sls %s''" % ' '.join(sls_opts)]
        else:
            LOGGER.debug('npx not found; falling back invoking sls shell '
                         'script directly.')
            sls_cmd = [
                os.path.join(self.path,
                             'node_modules',
                             '.bin',
                             'sls')
            ] + sls_opts

        if (not self.options.get('environments') and os.path.isfile(os.path.join(self.path, sls_env_file))) or (  # noqa pylint: disable=line-too-long
                self.options.get('environments', {}).get(self.context.env_name)):  # noqa
            if os.path.isfile(os.path.join(self.path, 'package.json')):
                with change_dir(self.path):
                    # Use npm ci if available (npm v5.7+)
                    if self.options.get('skip_npm_ci'):
                        LOGGER.info("Skipping npm ci or npm install on %s...",
                                    os.path.basename(self.path))
                    elif self.context.env_vars.get('CI') and use_npm_ci(self.path):  # noqa
                        LOGGER.info("Running npm ci on %s...",
                                    os.path.basename(self.path))
                        subprocess.check_call(['npm', 'ci'])
                    else:
                        LOGGER.info("Running npm install on %s...",
                                    os.path.basename(self.path))
                        subprocess.check_call(['npm', 'install'])
                    LOGGER.info("Running sls %s on %s (\"%s\")",
                                command,
                                os.path.basename(self.path),
                                # Strip out redundant npx quotes not needed
                                # when executing the command directly
                                " ".join(sls_cmd).replace('\'\'', '\''))
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
        result = self.run_serverless(command='deploy')
        warn_on_skipped_configs(result, self.context.env_name,
                                self.context.env_vars)

    def destroy(self):
        """Run serverless remove."""
        result = self.run_serverless(command='remove')
        warn_on_skipped_configs(result, self.context.env_name,
                                self.context.env_vars)
