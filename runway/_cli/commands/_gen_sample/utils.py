"""Utilities for gen-sample commands."""
import logging
import shutil
from pathlib import Path

from cfn_flip import to_yaml

from ....blueprints.tf_state import TfState
from ....cfngin.context import Context as CFNginContext

LOGGER = logging.getLogger(__name__.replace("._", "."))
ROOT = Path(__file__).parent.parent.parent.parent
TEMPLATES = ROOT / "templates"


def convert_gitignore(src):
    """Rename a gitignore template.

    Keyword Args:
        src (Path): Path object for source file.

    Returns:
        Optional[Path]: The renamed file if it was created.

    """
    gitignore = src.parent / ".gitignore"
    LOGGER.debug('renaming "%s" to "%s"', src, gitignore)
    src.rename(gitignore)
    return gitignore


def copy_sample(ctx, src, dest):
    """Copy a sample directory.

    Args:
        ctx (click.Context): Click context object.
        src (Path): Source path.
        dest (Path): Destination path.

    """
    if dest.exists():
        LOGGER.error("Directory %s already exists!", dest)
        ctx.exit(1)
    LOGGER.debug('copying "%s" to "%s"', src, dest)
    shutil.copytree(src, dest)


def write_tfstate_template(dest):
    # type: (Path) -> None
    """Write TfState blueprint as a YAML CFN template.

    Args:
        dest (Path): File to be written to.

    """
    LOGGER.debug('writing TfState as a YAML template to "%s"', dest)
    dest.write_text(
        to_yaml(TfState("test", CFNginContext({"namespace": "test"}), None).to_json())
    )
