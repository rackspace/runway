"""``runway gen-sample`` command group."""
import click

from .cdk_csharp import cdk_csharp
from .cdk_py import cdk_py
from .cdk_tsc import cdk_tsc
from .cfn import cfn
from .cfngin import cfngin
from .k8s_cfn_repo import k8s_cfn_repo
from .k8s_tf_repo import k8s_tf_repo
from .sls_py import sls_py
from .sls_tsc import sls_tsc
from .stacker import stacker
from .static_angular import static_angular
from .static_react import static_react
from .tf import tf

__all__ = [
    'cdk_csharp',
    'cdk_py',
    'cdk_tsc',
    'cfn',
    'cfngin',
    'k8s_cfn_repo',
    'k8s_tf_repo',
    'sls_py',
    'sls_tsc',
    'stacker',
    'static_angular',
    'static_react',
    'tf'
]

COMMANDS = [
    cdk_csharp,
    cdk_py,
    cdk_tsc,
    cfn,
    cfngin,
    k8s_cfn_repo,
    k8s_tf_repo,
    sls_py,
    sls_tsc,
    stacker,
    static_angular,
    static_react,
    tf
]


@click.group('gen-sample', short_help='generate sample module/project')
def gen_sample():
    """Generate a sample Runway module/project."""


for cmd in COMMANDS:  # register commands
    gen_sample.add_command(cmd)
