"""Generate a sample :ref:`Runway module<runway-module>` directory.

The sample module is created in the current directory. If a directory
already exists with the name it tries to use, it will not create the
sample directory.

.. rubric:: Available Samples

+--------------------+---------------------------------------------------+
|       Name         |  Description                                      |
+====================+===================================================+
| ``cdk-csharp``     | `AWS CDK`_ :ref:`module<runway-module>` using C#  |
+--------------------+---------------------------------------------------+
| ``cdk-py``         | `AWS CDK`_ :ref:`module<runway-module>` using     |
|                    | Python                                            |
+--------------------+---------------------------------------------------+
| ``cdk-tsc``        | `AWS CDK`_ :ref:`module<runway-module>` using     |
|                    | TypeScript                                        |
+--------------------+---------------------------------------------------+
| ``cfn``            | `CloudFormation`_ :ref:`module<runway-module>`    |
|                    | stack with S3 bucket & DDB table (perfect for     |
|                    | storing Terraform backend state)                  |
+--------------------+---------------------------------------------------+
| ``k8s-cfn-repo``   | `Kubernetes`_                                     |
|                    | :ref:`module<runway-module>` EKS cluster & sample |
|                    | app using CloudFormation                          |
+--------------------+---------------------------------------------------+
| ``k8s-tf-repo``    | `Kubernetes`_                                     |
|                    | :ref:`module<runway-module>` EKS cluster & sample |
|                    | app using Terraform                               |
+--------------------+---------------------------------------------------+
| ``sls-py``         | `Serverless Framework`_                           |
|                    | :ref:`module<runway-module>` using Python         |
+--------------------+---------------------------------------------------+
| ``sls-tsc``        | `Serverless Framework`_                           |
|                    | :ref:`module<runway-module>` using TypeScript     |
+--------------------+---------------------------------------------------+
| ``stacker``        | `Troposphere`_/`Stacker`_                         |
|                    | :ref:`module<runway-module>` identical the ``cfn``|
|                    | sample but with the template written in python    |
+--------------------+---------------------------------------------------+
| ``static-angular`` | `StaticSite`_                                     |
|                    | :ref:`module<runway-module>` of a StaticSite and  |
|                    | the Angular framework                             |
+--------------------+---------------------------------------------------+
| ``static-react``   | `StaticSite`_                                     |
|                    | :ref:`module<runway-module>` of a StaticSite and  |
|                    | the React framework                               |
+--------------------+---------------------------------------------------+
| ``tf``             | `Terraform`_ :ref:`module<runway-module>`         |
+--------------------+---------------------------------------------------+

.. rubric:: Example

.. code-block:: shell

    # create a "sampleapp.cfn" sample module directory
    $ runway gen-sample cfn

    # create a "runway-sample-tfstate.cfn" sample module directory
    $ runway gen-sample stacker

    # create a "sampleapp.sls" sample module directory
    $ runway gen-sample sls-py

"""
from __future__ import print_function
import logging
import os
import shutil
import sys

from cfn_flip import to_yaml

from ..runway_command import RunwayCommand
from ...cfngin.context import Context
from ...env_mgr.tfenv import get_latest_tf_version

LOGGER = logging.getLogger('runway')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def generate_tfstate_cfn_template():
    """Return rendered CFN template yaml."""
    from runway.blueprints.tf_state import TfState

    return to_yaml(TfState('test',
                           Context({"namespace": "test"}),
                           None).to_json())


def convert_gitignore(directory=''):
    """Given a directory convert the _gitignore file within to a dotfile.

    Keyword Args:
        directory (str)
    """
    os.rename(os.path.join(directory, '_gitignore'),
              os.path.join(directory, '.gitignore'))


def generate_sample_module(module_dir):
    """Generate skeleton sample module."""
    if os.path.isdir(module_dir):
        LOGGER.error("Error generating sample module -- directory %s "
                     "already exists!",
                     module_dir)
        sys.exit(1)
    os.mkdir(module_dir)


def generate_sample_static_angular(env_root):
    """Generate a sample static Angular application.

    Keyword Args:
        env_root (string): The environment root directory path
    """
    repo_dir = os.path.join(env_root, 'static-angular')

    if os.path.isdir(repo_dir):
        LOGGER.error("Error generating sample repo -- directory %s "
                     "already exists!",
                     repo_dir)
        sys.exit(1)

    shutil.copytree(
        os.path.join(ROOT, 'templates', 'static-angular'),
        repo_dir
    )
    convert_gitignore(os.path.join(repo_dir, 'sample-app'))

    LOGGER.info("Sample static Angular site repo created at %s",
                repo_dir)
    LOGGER.info('(see its README for setup and deployment instructions)')


def generate_sample_static_react(env_root):
    """Generate a sample static React application.

    Keyword Args:
        env_root (string): The environment root directory path
    """
    repo_dir = os.path.join(env_root, 'static-react')

    if os.path.isdir(repo_dir):
        LOGGER.error("Error generating sample repo -- directory %s "
                     "already exists!",
                     repo_dir)
        sys.exit(1)

    shutil.copytree(
        os.path.join(ROOT, 'templates', 'static-react'),
        repo_dir
    )
    convert_gitignore(os.path.join(repo_dir, 'sample-app'))

    LOGGER.info("Sample static React site repo created at %s",
                repo_dir)
    LOGGER.info('(see its README for setup and deployment instructions)')


def generate_sample_k8s_cfn_repo(env_root):
    """Generate sample k8s infrastructure repo."""
    repo_dir = os.path.join(env_root, 'k8s-cfn-infrastructure')
    if os.path.isdir(repo_dir):
        LOGGER.error("Error generating sample repo -- directory %s "
                     "already exists!",
                     repo_dir)
        sys.exit(1)

    from runway.blueprints.k8s.k8s_master import Cluster
    from runway.blueprints.k8s.k8s_iam import Iam
    from runway.blueprints.k8s.k8s_workers import NodeGroup as WorkerNodeGroup

    shutil.copytree(
        os.path.join(ROOT,
                     'templates',
                     'k8s-cfn-repo'),
        repo_dir
    )
    convert_gitignore(repo_dir)

    # Generate masters CFN templates from blueprints
    master_template_dir = os.path.join(repo_dir, 'k8s-master.cfn', 'templates')
    os.mkdir(master_template_dir)
    with open(os.path.join(master_template_dir, 'k8s_iam.yaml'), 'w') as stream:
        stream.write(to_yaml(Iam('test',
                                 Context({"namespace": "test"}),
                                 None).to_json()))
    with open(os.path.join(master_template_dir, 'k8s_master.yaml'), 'w') as stream:
        stream.write(to_yaml(Cluster('test',
                                     Context({"namespace": "test"}),
                                     None).to_json()))

    # Generate workers CFN template from blueprint
    worker_template_dir = os.path.join(repo_dir,
                                       'k8s-workers.cfn',
                                       'templates')
    os.mkdir(worker_template_dir)
    with open(os.path.join(worker_template_dir,
                           'k8s_workers.yaml'), 'w') as stream:
        stream.write(to_yaml(WorkerNodeGroup('test',
                                             Context({"namespace": "test"}),
                                             None).to_json()))

    LOGGER.info("Sample k8s infrastructure repo created at %s",
                repo_dir)
    LOGGER.info('(see its README for setup and deployment instructions)')


def generate_sample_k8s_tf_repo(env_root):
    """Generate sample k8s infrastructure repo."""
    repo_dir = os.path.join(env_root, 'k8s-tf-infrastructure')
    if os.path.isdir(repo_dir):
        LOGGER.error("Error generating sample repo -- directory %s "
                     "already exists!",
                     repo_dir)
        sys.exit(1)

    shutil.copytree(
        os.path.join(ROOT,
                     'templates',
                     'k8s-tf-repo'),
        repo_dir
    )

    # Use kubeconfig-generating hook from k8s_cfn_repo
    shutil.copyfile(
        os.path.join(ROOT,
                     'templates',
                     'k8s-cfn-repo',
                     'k8s-master.cfn',
                     'k8s_hooks',
                     'awscli.py'),
        os.path.join(repo_dir,
                     'gen-kubeconfig.cfn',
                     'k8s_hooks',
                     'awscli.py'),
    )

    convert_gitignore(repo_dir)

    # Generate tfstate CFN template from blueprints
    tfstate_template_dir = os.path.join(repo_dir, 'tfstate.cfn', 'templates')
    os.mkdir(tfstate_template_dir)
    with open(os.path.join(tfstate_template_dir, 'tf_state.yml'), 'w') as stream:
        stream.write(generate_tfstate_cfn_template())

    LOGGER.info("Sample k8s infrastructure repo created at %s",
                repo_dir)
    LOGGER.info('(see its README for setup and deployment instructions)')


def generate_sample_sls_module(env_root, template_dir, module_dir=None):
    """Generate skeleton Serverless sample module."""
    if module_dir is None:
        module_dir = os.path.join(env_root, 'sampleapp.sls')

    if os.path.isdir(module_dir):
        LOGGER.error("Error generating sample module -- directory %s "
                     "already exists!",
                     module_dir)
        sys.exit(1)

    shutil.copytree(
        os.path.join(ROOT,
                     'templates',
                     template_dir),
        module_dir
    )
    convert_gitignore(module_dir)
    LOGGER.info("Sample Serverless module created at %s",
                module_dir)
    LOGGER.info('To finish its setup, change to the %s directory and execute '
                '"npm install" to generate its lockfile.', module_dir)


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
    os.mkdir(os.path.join(module_dir, 'hello'))
    for i in ['hello/__init__.py', 'hello/hello_construct.py',
              'hello/hello_stack.py', '.gitignore', 'app.py', 'cdk.json',
              'package.json', 'Pipfile', 'Pipfile.lock', 'runway.module.yml']:
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
                '"npm install" to generate its lockfile.', module_dir)


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
        stream.write(generate_tfstate_cfn_template())
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
                         'blueprints',
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

    SKIP_FIND_CONFIG = True

    # noqa pylint: disable=too-many-branches
    def execute(self):
        """Run selected module generator."""
        if self._cli_arguments.get('<samplename>') == 'cfn':
            generate_sample_cfn_module(self.env_root)
        elif self._cli_arguments.get('<samplename>') == 'static-angular':
            generate_sample_static_angular(self.env_root)
        elif self._cli_arguments.get('<samplename>') == 'static-react':
            generate_sample_static_react(self.env_root)
        elif self._cli_arguments.get('<samplename>') == 'sls-py':
            generate_sample_sls_module(self.env_root, 'sls-py')
        elif self._cli_arguments.get('<samplename>') == 'sls-tsc':
            generate_sample_sls_module(self.env_root, 'sls-tsc')
        elif self._cli_arguments.get('<samplename>') == 'stacker':
            generate_sample_stacker_module(self.env_root)
        elif self._cli_arguments.get('<samplename>') == 'tf':
            generate_sample_tf_module(self.env_root)
        elif self._cli_arguments.get('<samplename>') == 'k8s-cfn-repo':
            generate_sample_k8s_cfn_repo(self.env_root)
        elif self._cli_arguments.get('<samplename>') == 'k8s-tf-repo':
            generate_sample_k8s_tf_repo(self.env_root)
        elif self._cli_arguments.get('<samplename>') == 'cdk-tsc':
            generate_sample_cdk_tsc_module(self.env_root)
        elif self._cli_arguments.get('<samplename>') == 'cdk-py':
            generate_sample_cdk_py_module(self.env_root)
        elif self._cli_arguments.get('<samplename>') == 'cdk-csharp':
            generate_sample_cdk_cs_module(self.env_root)
        else:
            LOGGER.info("Available samples to generate:")
            for i in ['cfn', 'static-angular', 'static-react', 'sls-tsc',
                      'sls-py', 'tf', 'k8s-cfn-repo', 'k8s-tf-repo',
                      'stacker', 'cdk-tsc', 'cdk-py', 'cdk-csharp']:
                print(i)
