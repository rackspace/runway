"""``runway gen-sample k8s-flux-repo`` command."""
import logging
import shutil
import sys
from typing import Any  # pylint: disable=W

import click

from ... import options
from .utils import TEMPLATES, convert_gitignore, copy_sample, write_tfstate_template

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E

LOGGER = logging.getLogger(__name__.replace("._", "."))


@click.command("k8s-flux-repo", short_help="k8s + flux + tf (k8s-tf-infrastructure)")
@options.debug
@options.no_color
@options.verbose
@click.pass_context
def k8s_flux_repo(ctx, **_):
    # type: (click.Context, Any) -> None
    """Generate a sample Kubernetes cluster with Flux CD managed via Terraform."""
    src = TEMPLATES / "k8s-flux-repo"
    dest = Path.cwd() / "k8s-tf-infrastructure"
    src_awscli = TEMPLATES / "k8s-cfn-repo/k8s-master.cfn/k8s_hooks/awscli.py"
    dest_awscli = dest / "gen-kubeconfig.cfn/k8s_hooks/awscli.py"

    copy_sample(ctx, src, dest)
    tf_eks_base = TEMPLATES / "k8s-tf-repo" / "eks-base.tf"
    copy_sample(ctx, tf_eks_base, dest / tf_eks_base.parts[-1])
    convert_gitignore(dest / "_gitignore")

    gen_kubeconfig_src_dir = TEMPLATES / "k8s-tf-repo" / "gen-kubeconfig.cfn"
    copy_sample(ctx, gen_kubeconfig_src_dir, dest / gen_kubeconfig_src_dir.parts[-1])
    LOGGER.debug('copying "%s" to "%s"', src_awscli, dest_awscli)
    shutil.copyfile(str(src_awscli), str(dest_awscli))

    tfstate_src_dir = TEMPLATES / "k8s-tf-repo" / "tfstate.cfn"
    copy_sample(ctx, tfstate_src_dir, dest / tfstate_src_dir.parts[-1])
    tfstate_templates_dir = dest / "tfstate.cfn/templates"
    tfstate_templates_dir.mkdir()
    write_tfstate_template(tfstate_templates_dir / "tf_state.yml")

    LOGGER.success("Sample k8s infrastructure repo created at %s", dest)
    LOGGER.notice("See the README for setup and deployment instructions.")
