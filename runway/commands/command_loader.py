"""command class loader."""

import importlib

from inspect import getmembers, isclass

ALL_COMMANDS_MODULE = importlib.import_module("runway.commands")


def find_command_class(command_name):
    """Try to find a class for the given command name."""
    if hasattr(ALL_COMMANDS_MODULE, command_name):
        command_module = getattr(ALL_COMMANDS_MODULE, command_name)
        command_class_hierarchy = getmembers(command_module, isclass)
        command_class_tuple = list(filter(_not_base_class, command_class_hierarchy))[0]
        return command_class_tuple[1]
    return None


def _not_base_class(name_class_pair):
    return name_class_pair[0] not in ['RunwayCommand', 'ModuleCommand']
