"""Hook utils."""
import collections
import logging
import os
import sys
from types import FunctionType

from runway.util import load_object_from_string
from runway.variables import Variable, resolve_variables

from ..blueprints.base import Blueprint
from ..exceptions import FailedVariableLookup

LOGGER = logging.getLogger(__name__)


class BlankBlueprint(Blueprint):
    """Blueprint that can be built programatically."""

    def create_template(self):
        """Create template without raising NotImplementedError."""


def full_path(path):
    """Return full path."""
    return os.path.abspath(os.path.expanduser(path))


# TODO split up to reduce number of statements
def handle_hooks(  # pylint: disable=too-many-statements
    stage, hooks, provider, context
):
    """Handle pre/post_build hooks.

    These are pieces of code that we want to run before/after the builder
    builds the stacks.

    Args:
        stage (str): The current stage (pre_run, post_run, etc).
        hooks (List[:class:`runway.cfngin.config.Hook`]): Hooks to execute.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`): Provider
            instance.
        context (:class:`runway.cfngin.context.Context`): Context instance.

    """
    if not hooks:
        LOGGER.debug("no %s hooks defined", stage)
        return

    hook_paths = []
    for i, hook in enumerate(hooks):
        try:
            hook_paths.append(hook.path)
        except KeyError:
            raise ValueError("%s hook #%d missing path." % (stage, i))

    LOGGER.info("executing %s hooks: %s", stage, ", ".join(hook_paths))
    stage = stage.replace("build", "deploy")  # TODO remove after full rename
    for hook in hooks:
        data_key = hook.data_key
        required = hook.required

        if not hook.enabled:
            LOGGER.debug("hook with method %s is disabled; skipping", hook.path)
            continue

        try:
            method = load_object_from_string(hook.path, try_reload=True)
        except (AttributeError, ImportError):
            LOGGER.exception("unable to load method at %s", hook.path)
            if required:
                raise
            continue

        if isinstance(hook.args, dict):
            args = [Variable(k, v) for k, v in hook.args.items()]
            try:  # handling for output or similar being used in pre_build
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
            kwargs = {v.name: v.value for v in args}
        else:
            kwargs = hook.args or {}

        try:
            if isinstance(method, FunctionType):
                result = method(context=context, provider=provider, **kwargs)
            else:
                result = getattr(
                    method(context=context, provider=provider, **kwargs), stage
                )()
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("method %s threw an exception", hook.path)
            if required:
                raise
            continue

        if not result:
            if required:
                LOGGER.error(
                    "required hook %s failed; return value: %s", hook.path, result
                )
                sys.exit(1)
            LOGGER.warning(
                "non-required hook %s failed; return value: %s", hook.path, result
            )
        else:
            if isinstance(result, collections.Mapping):
                if data_key:
                    LOGGER.debug(
                        "adding result for hook %s to context in data_key %s",
                        hook.path,
                        data_key,
                    )
                    context.set_hook_data(data_key, result)
                else:
                    LOGGER.debug(
                        "hook %s returned result data but no data key set; ignoring",
                        hook.path,
                    )
