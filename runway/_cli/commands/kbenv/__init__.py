"""``runway kbenv`` command group."""
import click

from .install import install
from .run import run


__all__ = ['install', 'run']

COMMANDS = [install, run]


@click.group('kbenv', short_help='kubectl (install|run)')
def kbenv():
    """kubectl version management and execution.

    Compatible with https://github.com/alexppg/kbenv.

    """


for cmd in COMMANDS:  # register commands
    kbenv.add_command(cmd)
