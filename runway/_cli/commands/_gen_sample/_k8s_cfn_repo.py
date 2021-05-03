"""``runway gen-sample k8s-cfn`` command."""
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click
from cfn_flip import to_yaml

from ....blueprints.k8s.k8s_iam import Iam
from ....blueprints.k8s.k8s_master import Cluster
from ....blueprints.k8s.k8s_workers import NodeGroup
from ....context import CfnginContext
from ... import options
from .utils import TEMPLATES, convert_gitignore, copy_sample

if TYPE_CHECKING:
    from ...._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("k8s-cfn-repo", short_help="k8s + cfn (k8s-cfn-infrastructure)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def k8s_cfn_repo(ctx: click.Context, **_: Any) -> None:
    """Generate a sample CloudFormation project using Kubernetes."""
    src = TEMPLATES / "k8s-cfn-repo"
    dest = Path.cwd() / "k8s-cfn-infrastructure"

    copy_sample(ctx, src, dest)
    convert_gitignore(dest / "_gitignore")

    master_templates = dest / "k8s-master.cfn/templates"
    worker_templates = dest / "k8s-workers.cfn/templates"
    env = {"namespace": "test"}

    LOGGER.verbose("rendering master templates...")
    master_templates.mkdir()
    (master_templates / "k8s_iam.yaml").write_text(
        to_yaml(Iam("test", CfnginContext(environment=env.copy())).to_json())
    )
    (master_templates / "k8s_master.yaml").write_text(
        to_yaml(Cluster("test", CfnginContext(environment=env.copy())).to_json())
    )

    LOGGER.verbose("rendering worker templates...")
    worker_templates.mkdir()
    (worker_templates / "k8s_workers.yaml").write_text(
        to_yaml(NodeGroup("test", CfnginContext(environment=env.copy())).to_json())
    )

    LOGGER.success("Sample k8s infrastructure repo created at %s", dest)
    LOGGER.notice("See the README for setup and deployment instructions.")
