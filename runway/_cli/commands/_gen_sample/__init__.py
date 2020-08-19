"""``runway gen-sample`` command group."""
# docs: file://./../../../../docs/source/commands.rst
import click

from ... import options
from ._cdk_csharp import cdk_csharp
from ._cdk_py import cdk_py
from ._cdk_tsc import cdk_tsc
from ._cfn import cfn
from ._cfngin import cfngin
from ._k8s_cfn_repo import k8s_cfn_repo
from ._k8s_tf_repo import k8s_tf_repo
from ._sls_py import sls_py
from ._sls_tsc import sls_tsc
from ._stacker import stacker
from ._static_angular import static_angular
from ._static_react import static_react
from ._tf import tf

__all__ = [
    "cdk_csharp",
    "cdk_py",
    "cdk_tsc",
    "cfn",
    "cfngin",
    "k8s_cfn_repo",
    "k8s_tf_repo",
    "sls_py",
    "sls_tsc",
    "stacker",
    "static_angular",
    "static_react",
    "tf",
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
    tf,
]


@click.group("gen-sample", short_help="generate sample module/project")
@options.debug
@options.no_color
@options.verbose
def gen_sample(**_):
    """Generate a sample Runway module module/project.

    The sample is created in the current directory.
    If a directory already exists with the name Runway tries to use,
    the sample will not be created.

    """


for cmd in COMMANDS:  # register commands
    gen_sample.add_command(cmd)
