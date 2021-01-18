"""``runway gen-sample k8s-tf`` command."""
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click

from ... import options
from .utils import TEMPLATES, convert_gitignore, copy_sample, write_tfstate_template

if TYPE_CHECKING:
    from ...._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


@click.command("k8s-tf-repo", short_help="k8s + tf (k8s-tf-infrastructure)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def k8s_tf_repo(ctx: click.Context, **_: Any) -> None:
    """Generate a sample Terraform project using Kubernetes."""
    src = TEMPLATES / "k8s-tf-repo"
    dest = Path.cwd() / "k8s-tf-infrastructure"
    src_awscli = TEMPLATES / "k8s-cfn-repo/k8s-master.cfn/k8s_hooks/awscli.py"
    dest_awscli = dest / "gen-kubeconfig.cfn/k8s_hooks/awscli.py"

    copy_sample(ctx, src, dest)
    LOGGER.debug('copying "%s" to "%s"', src_awscli, dest_awscli)
    shutil.copyfile(src_awscli, dest_awscli)
    convert_gitignore(dest / "_gitignore")

    tfstate_dir = dest / "tfstate.cfn/templates"
    tfstate_dir.mkdir()
    write_tfstate_template(tfstate_dir / "tf_state.yml")

    LOGGER.success("Sample k8s infrastructure repo created at %s", dest)
    LOGGER.notice("See the README for setup and deployment instructions.")
