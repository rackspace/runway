"""The gen-sample command."""
import logging
import os
import shutil
from subprocess import check_output
import sys

import cfn_flip

from ..runway_command import RunwayCommand
from ...tfenv import get_latest_tf_version

LOGGER = logging.getLogger('runway')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def generate_sample_module(module_dir):
    """Generate skeleton sample module."""
    if os.path.isdir(module_dir):
        LOGGER.error("Error generating sample module -- directory %s "
                     "already exists!",
                     module_dir)
        sys.exit(1)
    os.mkdir(module_dir)


def generate_sample_sls_module(env_root, module_dir=None):
    """Generate skeleton Serverless sample module."""
    if module_dir is None:
        module_dir = os.path.join(env_root, 'sampleapp.sls')
    generate_sample_module(module_dir)
    for i in ['config-dev-us-east-1.json', 'handler.py', 'package.json',
              'serverless.yml']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'serverless',
                         i),
            os.path.join(module_dir, i),
        )
    LOGGER.info("Sample Serverless module created at %s",
                module_dir)


def generate_sample_sls_tsc_module(env_root, module_dir=None):
    """Generate skeleton Serverless TypeScript sample module."""
    if module_dir is None:
        module_dir = os.path.join(env_root, 'sampleapp.sls')
    generate_sample_module(module_dir)
    for i in ['package.json', 'serverless.yml', 'tsconfig.json',
              'webpack.config.js']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'sls-tsc',
                         i),
            os.path.join(module_dir, i),
        )
    os.mkdir(os.path.join(module_dir, 'src'))
    for i in ['handler.spec.ts', 'handler.ts']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'sls-tsc',
                         'src',
                         i),
            os.path.join(module_dir, 'src', i),
        )
    LOGGER.info("Sample Serverless TypeScript module created at %s",
                module_dir)


def generate_sample_cdk_tsc_module(env_root, module_dir=None):
    """Generate skeleton CDK TS sample module."""
    if module_dir is None:
        module_dir = os.path.join(env_root, 'sampleapp.cdk')
    generate_sample_module(module_dir)
    for i in ['.npmignore', 'cdk.json', 'package.json', 'runway.module.yml',
              'tsconfig.json', 'README.md']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'cdk-tsc',
                         i),
            os.path.join(module_dir, i),
        )
    for i in [['bin', 'sample.ts'], ['lib', 'sample-stack.ts']]:
        os.mkdir(os.path.join(module_dir, i[0]))
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'cdk-tsc',
                         i[0],
                         i[1]),
            os.path.join(module_dir, i[0], i[1]),
        )
    with open(os.path.join(module_dir, '.gitignore'), 'w') as stream:
        stream.write('*.js\n')
        stream.write('*.d.ts\n')
        stream.write('node_modules\n')
    LOGGER.info("Sample CDK module created at %s", module_dir)
    LOGGER.info('To finish its setup, change to the %s directory and execute '
                '"npm install" to generate its lockfile.', module_dir)


def generate_sample_cdk_cs_module(env_root, module_dir=None):
    """Generate skeleton CDK C# sample module."""
    if module_dir is None:
        module_dir = os.path.join(env_root, 'sampleapp.cdk')
    generate_sample_module(module_dir)
    for i in ['add-project.hook.d.ts', 'cdk.json', 'package.json',
              'runway.module.yml', 'README.md']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'cdk-csharp',
                         i),
            os.path.join(module_dir, i),
        )
    shutil.copyfile(
        os.path.join(ROOT,
                     'templates',
                     'cdk-csharp',
                     'dot_gitignore'),
        os.path.join(module_dir, '.gitignore'),
    )
    os.mkdir(os.path.join(module_dir, 'src'))
    shutil.copyfile(
        os.path.join(ROOT,
                     'templates',
                     'cdk-csharp',
                     'src',
                     'HelloCdk.sln'),
        os.path.join(module_dir, 'src', 'HelloCdk.sln'),
    )
    os.mkdir(os.path.join(module_dir, 'src', 'HelloCdk'))
    for i in ['HelloCdk.csproj', 'HelloConstruct.cs', 'HelloStack.cs',
              'Program.cs']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'cdk-csharp',
                         'src',
                         'HelloCdk',
                         i),
            os.path.join(module_dir, 'src', 'HelloCdk', i),
        )
    LOGGER.info("Sample C# CDK module created at %s", module_dir)
    LOGGER.info('To finish its setup, change to the %s directory and execute '
                '"npm install" to generate its lockfile.', module_dir)


def generate_sample_cdk_py_module(env_root, module_dir=None):
    """Generate skeleton CDK python sample module."""
    if module_dir is None:
        module_dir = os.path.join(env_root, 'sampleapp.cdk')
    generate_sample_module(module_dir)
    for i in ['app.py', 'cdk.json', 'lambda-index.py', 'package.json',
              'runway.module.yml', 'Pipfile']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'cdk-py',
                         i),
            os.path.join(module_dir, i),
        )
    with open(os.path.join(module_dir, '.gitignore'), 'w') as stream:
        stream.write('node_modules')
    LOGGER.info("Sample CDK module created at %s", module_dir)
    LOGGER.info('To finish its setup, change to the %s directory and execute '
                '"npm install" and "pipenv update -d --three" to generate its '
                'lockfiles.', module_dir)


def generate_sample_cfn_module(env_root, module_dir=None):
    """Generate skeleton CloudFormation sample module."""
    if module_dir is None:
        module_dir = os.path.join(env_root, 'sampleapp.cfn')
    generate_sample_module(module_dir)
    for i in ['stacks.yaml', 'dev-us-east-1.env']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'cfn',
                         i),
            os.path.join(module_dir, i)
        )
    os.mkdir(os.path.join(module_dir, 'templates'))
    with open(os.path.join(module_dir,
                           'templates',
                           'tf_state.yml'), 'w') as stream:
        stream.write(
            cfn_flip.flip(
                check_output(
                    [sys.executable,
                     os.path.join(ROOT,
                                  'templates',
                                  'stacker',
                                  'tfstate_blueprints',
                                  'tf_state.py')]
                )

            )
        )
    LOGGER.info("Sample CloudFormation module created at %s",
                module_dir)


def generate_sample_stacker_module(env_root, module_dir=None):
    """Generate skeleton Stacker sample module."""
    if module_dir is None:
        module_dir = os.path.join(env_root,
                                  'runway-sample-tfstate.cfn')
    generate_sample_module(module_dir)
    for i in ['stacks.yaml', 'dev-us-east-1.env']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'stacker',
                         i),
            os.path.join(module_dir, i)
        )
    os.mkdir(os.path.join(module_dir, 'tfstate_blueprints'))
    for i in ['__init__.py', 'tf_state.py']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'stacker',
                         'tfstate_blueprints',
                         i),
            os.path.join(module_dir, 'tfstate_blueprints', i)
        )
    os.chmod(  # make blueprint executable
        os.path.join(module_dir, 'tfstate_blueprints', 'tf_state.py'),
        os.stat(os.path.join(module_dir,
                             'tfstate_blueprints',
                             'tf_state.py')).st_mode | 0o0111
    )
    LOGGER.info("Sample Stacker module created at %s",
                module_dir)


def generate_sample_tf_module(env_root, module_dir=None):
    """Generate skeleton Terraform sample module."""
    if module_dir is None:
        module_dir = os.path.join(env_root, 'sampleapp.tf')
    generate_sample_module(module_dir)
    for i in ['backend-us-east-1.tfvars', 'dev-us-east-1.tfvars', 'main.tf']:
        shutil.copyfile(
            os.path.join(ROOT,
                         'templates',
                         'terraform',
                         i),
            os.path.join(module_dir, i),
        )
    tf_ver_template = os.path.join(ROOT,
                                   'templates',
                                   'terraform',
                                   '.terraform-version')
    if os.path.isfile(tf_ver_template):
        shutil.copyfile(
            tf_ver_template,
            os.path.join(module_dir, '.terraform-version'),
        )
    else:  # running directly from git
        latest_tf_ver = get_latest_tf_version()
        with open(os.path.join(module_dir,
                               '.terraform-version'), 'w') as stream:
            stream.write(latest_tf_ver)

    LOGGER.info("Sample Terraform app created at %s",
                module_dir)


class GenSample(RunwayCommand):
    """Extend Base with execute to run the module generators."""

    def execute(self):
        """Run selected module generator."""
        if self._cli_arguments['cfn']:
            generate_sample_cfn_module(self.env_root)
        elif self._cli_arguments['sls']:
            generate_sample_sls_module(self.env_root)
        elif self._cli_arguments['sls-tsc']:
            generate_sample_sls_tsc_module(self.env_root)
        elif self._cli_arguments['stacker']:
            generate_sample_stacker_module(self.env_root)
        elif self._cli_arguments['tf']:
            generate_sample_tf_module(self.env_root)
        elif self._cli_arguments['cdk-tsc']:
            generate_sample_cdk_tsc_module(self.env_root)
        elif self._cli_arguments['cdk-py']:
            generate_sample_cdk_py_module(self.env_root)
        elif self._cli_arguments['cdk-csharp']:
            generate_sample_cdk_cs_module(self.env_root)
