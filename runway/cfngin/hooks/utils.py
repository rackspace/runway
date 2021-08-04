"""Hook utils."""
from __future__ import annotations

import collections.abc
import logging
import os
import sys
from typing import TYPE_CHECKING, Any, Dict, List

import pydantic

from ...exceptions import FailedVariableLookup
from ...utils import BaseModel, load_object_from_string
from ...variables import Variable, resolve_variables
from ..blueprints.base import Blueprint

if TYPE_CHECKING:
    from ...config.models.cfngin import CfnginHookDefinitionModel
    from ...context import CfnginContext
    from ..providers.aws.default import Provider

LOGGER = logging.getLogger(__name__)


class BlankBlueprint(Blueprint):
    """Blueprint that can be built programatically."""

    def create_template(self) -> None:
        """Create template without raising NotImplementedError."""


class TagDataModel(BaseModel):
    """AWS Resource Tag data model."""

    key: str = pydantic.Field(..., alias="Key")
    value: str = pydantic.Field(..., alias="Value")

    class Config:
        """Model configuration."""

        allow_population_by_field_name = True
        extra = pydantic.Extra.forbid


def full_path(path: str) -> str:
    """Return full path."""
    return os.path.abspath(os.path.expanduser(path))


# TODO split up to reduce number of statements
def handle_hooks(  # pylint: disable=too-many-statements
    stage: str,
    hooks: List[CfnginHookDefinitionModel],
    provider: Provider,
    context: CfnginContext,
):
    """Handle pre/post_deploy hooks.

    These are pieces of code that we want to run before/after deploying
    stacks.

    Args:
        stage: The current stage (pre_run, post_run, etc).
        hooks: Hooks to execute.
        provider: Provider instance.
        context: Context instance.

    """
    if not hooks:
        LOGGER.debug("no %s hooks defined", stage)
        return

    hook_paths: List[str] = []
    for i, hook in enumerate(hooks):
        try:
            hook_paths.append(hook.path)
        except KeyError as exc:
            raise ValueError(f"{stage} hook #{i} missing path.") from exc

    LOGGER.info("executing %s hooks: %s", stage, ", ".join(hook_paths))
    for hook in hooks:
        if not hook.enabled:
            LOGGER.debug("hook with method %s is disabled; skipping", hook.path)
            continue

        try:
            method = load_object_from_string(hook.path, try_reload=True)
        except (AttributeError, ImportError):
            LOGGER.exception("unable to load method at %s", hook.path)
            if hook.required:
                raise
            continue

        if hook.args:
            args = [Variable(k, v) for k, v in hook.args.items()]
            try:  # handling for output or similar being used in pre_deploy
                resolve_variables(args, context, provider)
            except FailedVariableLookup:
                if "pre" in stage:
                    LOGGER.error(
                        "lookups that change the order of execution, like "
                        '"output", can only be used in "post_*" hooks; '
                        "please ensure that the hook being used does "
                        "not rely on a stack, hook_data, or context that "
                        "does not exist yet"
                    )
                raise
            kwargs: Dict[str, Any] = {v.name: v.value for v in args}
        else:
            kwargs = {}

        try:
            if isinstance(method, type):
                result = getattr(
                    method(context=context, provider=provider, **kwargs), stage
                )()
            else:
                result = method(context=context, provider=provider, **kwargs)
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("hook %s threw an exception", hook.path)
            if hook.required:
                raise
            continue

        if not result:
            if hook.required:
                LOGGER.error(
                    "required hook %s failed; return value: %s", hook.path, result
                )
                sys.exit(1)
            LOGGER.warning(
                "non-required hook %s failed; return value: %s", hook.path, result
            )
        else:
            if isinstance(result, (collections.abc.Mapping, pydantic.BaseModel)):
                if hook.data_key:
                    LOGGER.debug(
                        "adding result for hook %s to context in data_key %s",
                        hook.path,
                        hook.data_key,
                    )
                    context.set_hook_data(hook.data_key, result)
                else:
                    LOGGER.debug(
                        "hook %s returned result data but no data key set; ignoring",
                        hook.path,
                    )
