"""'Git' type Path Source."""
from __future__ import absolute_import
# pylint: disable=unused-import
from typing import List, Dict, Optional, Union  # noqa: F401

import tempfile
import shutil
import subprocess

import os
import sys
import logging

from .source import Source

LOGGER = logging.getLogger('runway')


class Git(Source):
    """Git type Path Source."""

    def fetch(self):
        # type: () -> str
        """Retrieve the git repository from it's remote location."""
        from git import Repo

        ref = self.determine_git_ref()  # type: str
        dir_name = '_'.join([
            self.sanitize_git_path(self.config.get('uri', '')),
            ref
        ])  # type: str
        cached_dir_path = os.path.join(self.cache_dir, dir_name)  # type: str
        cached_path = ''  # type: str

        if not os.path.isdir(cached_dir_path):
            tmp_dir = tempfile.mkdtemp()
            try:
                tmp_repo_path = os.path.join(tmp_dir, dir_name)  # type: str
                with Repo.clone_from(self.config.get('uri'), tmp_repo_path) as repo:
                    repo.head.reference = ref  # type: str
                    repo.head.reset(index=True, working_tree=True)
                shutil.move(tmp_repo_path, self.cache_dir)
                cached_path = os.path.join(self.cache_dir, dir_name)  # type: str
            finally:
                shutil.rmtree(tmp_dir)
        else:
            cached_path = cached_dir_path  # type: str

        return os.path.join(cached_path, self.config['location'])

    def git_ls_remote(self, ref):
        # type: (str) -> str
        """List remote repositories based on uri and ref received."""
        LOGGER.debug(
            "Invoking git to retrieve commit id for repo %s...",
            self.config.get('uri', '')
        )
        lsremote_output = subprocess.check_output(['git',
                                                   'ls-remote',
                                                   self.config.get('uri', ''),
                                                   ref])
        # pylint: disable=unsupported-membership-test
        if b"\t" in lsremote_output:
            commit_id = lsremote_output.split(b"\t")[0]  # type List[str]
            LOGGER.debug("Matching commit id found: %s", commit_id)
            return commit_id
        raise ValueError("Ref \"%s\" not found for repo %s." % (ref, self.config['uri']))

    def determine_git_ls_remote_ref(self):
        # type: () -> str
        """Determine remote ref, defaulting to HEAD unless a branch is found."""
        ref = "HEAD"

        if self.config.get('branch'):
            ref = "refs/heads/%s" % self.config.get('branch')  # type: str

        return ref

    def determine_git_ref(self):
        # type: () -> str
        """Determine the git reference code."""
        ref_config_keys = 0   # type: int
        options = self.config.get('options')  # type: Dict[str, Union(str, Dict[str, str])]

        for i in ['commit', 'tag', 'branch']:
            if options.get(i):
                ref_config_keys += 1
        if ref_config_keys > 1:
            raise ImportError("Fetching remote git sources failed: "
                              "conflicting revisions (e.g. 'commit', 'tag', "
                              "'branch') specified for a package source")

        if options.get('commit'):
            ref = options.get('commit')  # type: str
        elif options.get('tag'):
            ref = options.get('tag')  # type: str
        else:
            ref = self.git_ls_remote(self.determine_git_ls_remote_ref())  # ty pe: str
        if sys.version_info[0] > 2 and isinstance(ref, bytes):
            return ref.decode()
        return ref

    def sanitize_git_path(self, path):
        # type(str) -> str
        """Sanitize the git path for folder/file assignment."""
        dir_name = path  # type: str
        split = path.split('//')  # type: List[str]
        domain = split[len(split)-1]  # type: str

        if domain.endswith('.git'):
            dir_name = domain[:-4]

        return self.sanitize_directory_path(dir_name)
