"""Hook utils."""
import collections
import logging
import os
import sys

from ...util import load_object_from_string

LOGGER = logging.getLogger(__name__)


def full_path(path):
    """Return full path."""
    return os.path.abspath(os.path.expanduser(path))


def handle_hooks(stage, hooks, provider, context):
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
        LOGGER.debug("No %s hooks defined.", stage)
        return

    hook_paths = []
    for i, hook in enumerate(hooks):
        try:
            hook_paths.append(hook.path)
        except KeyError:
            raise ValueError("%s hook #%d missing path." % (stage, i))

    LOGGER.info("Executing %s hooks: %s", stage, ", ".join(hook_paths))
    for hook in hooks:
        data_key = hook.data_key
        required = hook.required
        kwargs = hook.args or {}
        enabled = hook.enabled
        if not enabled:
            LOGGER.debug("hook with method %s is disabled, skipping",
                         hook.path)
            continue
        try:
            method = load_object_from_string(hook.path)
        except (AttributeError, ImportError):
            LOGGER.exception("Unable to load method at %s:", hook.path)
            if required:
                raise
            continue
        try:
            result = method(context=context, provider=provider, **kwargs)
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Method %s threw an exception:", hook.path)
            if required:
                raise
            continue
        if not result:
            if required:
                LOGGER.error("Required hook %s failed. Return value: %s",
                             hook.path, result)
                sys.exit(1)
            LOGGER.warning("Non-required hook %s failed. Return value: %s",
                           hook.path, result)
        else:
            if isinstance(result, collections.Mapping):
                if data_key:
                    LOGGER.debug("Adding result for hook %s to context in "
                                 "data_key %s.", hook.path, data_key)
                    context.set_hook_data(data_key, result)
                else:
                    LOGGER.debug("Hook %s returned result data, but no data "
                                 "key set, so ignoring.", hook.path)
