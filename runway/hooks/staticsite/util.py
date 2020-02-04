"""Utility functions for website build/upload."""

import hashlib
import logging
import os

import zgitignore

from ...util import change_dir

LOGGER = logging.getLogger(__name__)


def calculate_hash_of_files(files, root):
    """Return a hash of all of the given files at the given root.

    Adapted from stacker.hooks.aws_lambda; used according to its license:
    https://github.com/cloudtools/stacker/blob/1.4.0/LICENSE

    Args:
        files (list[str]): file names to include in the hash calculation,
            relative to ``root``.
        root (str): base directory to analyze files in.
    Returns:
        str: A hash of the hashes of the given files.

    """
    file_hash = hashlib.md5()
    for fname in sorted(files):
        fileobj = os.path.join(root, fname)
        file_hash.update((fname + "\0").encode())
        with open(fileobj, "rb") as filedes:
            for chunk in iter(lambda: filedes.read(4096), ""):  # noqa pylint: disable=cell-var-from-loop
                if not chunk:
                    break
                file_hash.update(chunk)
            file_hash.update("\0".encode())

    return file_hash.hexdigest()


def get_hash_of_files(root_path, directories=None):
    """Generate md5 hash of files."""
    if not directories:
        directories = [{'path': './'}]

    files_to_hash = []
    for i in directories:
        ignorer = get_ignorer(os.path.join(root_path, i['path']),
                              i.get('exclusions'))

        with change_dir(root_path):
            for root, dirs, files in os.walk(i['path'], topdown=True):
                if (root != './') and ignorer.is_ignored(root, True):
                    dirs[:] = []
                    files[:] = []
                else:
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        if not ignorer.is_ignored(filepath):
                            files_to_hash.append(
                                filepath[2:] if filepath.startswith('./') else filepath  # noqa
                            )

    return calculate_hash_of_files(files_to_hash, root_path)


def get_ignorer(path, additional_exclusions=None):
    """Create ignorer with directory gitignore file."""
    ignorefile = zgitignore.ZgitIgnore()
    gitignore_file = os.path.join(path, '.gitignore')
    if os.path.isfile(gitignore_file):
        with open(gitignore_file, 'r') as fileobj:
            ignorefile.add_patterns(fileobj.read().splitlines())

    if additional_exclusions is not None:
        ignorefile.add_patterns(additional_exclusions)

    return ignorefile
