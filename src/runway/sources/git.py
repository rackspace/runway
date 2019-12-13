from .source import Source
import tempfile
import shutil
import subprocess

import os
import sys
import six
import logging

LOGGER = logging.getLogger('runway')

class Git(Source):
    def __init__(self, config, cache_dir=None):
      self.config = config
      self.cache_dir = cache_dir

    def fetch(self):
        from git import Repo

        ref = self.determine_git_ref()
        dir_name = '_'.join([self.sanitize_git_path(self.config['uri']), ref])
        cached_dir_path = os.path.join(self.cache_dir, dir_name)
        cached_path = ''

        if not os.path.isdir(cached_dir_path):
            tmp_dir = tempfile.mkdtemp()
            try:
                tmp_repo_path = os.path.join(tmp_dir, dir_name)
                with Repo.clone_from(self.config['uri'], tmp_repo_path) as repo:
                    repo.head.reference = ref
                    repo.head.reset(index=True, working_tree=True)
                shutil.move(tmp_repo_path, self.cache_dir)
                cached_path = os.path.join(self.cache_dir, dir_name)
            finally:
                shutil.rmtree(tmp_dir)
        else:
            cached_path = cached_dir_path

        return os.path.join(cached_path, self.config['location'])

    def git_ls_remote(self, ref):
        LOGGER.debug("Invoking git to retrieve commit id for repo %s...", self.config['uri'])
        lsremote_output = subprocess.check_output(['git',
                                                   'ls-remote',
                                                   self.config['uri'],
                                                   ref])
        if b"\t" in lsremote_output:
            commit_id = lsremote_output.split(b"\t")[0]
            LOGGER.debug("Matching commit id found: %s", commit_id)
            return commit_id
        else:
            raise ValueError("Ref \"%s\" not found for repo %s." % (ref, self.config['uri']))

    def determine_git_ls_remote_ref(self):
        if self.config.get('branch'):
            ref = "refs/heads/%s" % self.config['branch']
        else:
            ref = "HEAD"

        return ref

    def determine_git_ref(self):
        ref_config_keys = 0
        for i in ['commit', 'tag', 'branch']:
            if self.config.get(i):
                ref_config_keys += 1
        if ref_config_keys > 1:
            raise ImportError("Fetching remote git sources failed: "
                              "conflicting revisions (e.g. 'commit', 'tag', "
                              "'branch') specified for a package source")

        if self.config.get('commit'):
            ref = self.config['commit']
        elif self.config.get('tag'):
            ref = self.config['tag']
        else:
            ref = self.git_ls_remote(self.determine_git_ls_remote_ref())
        if sys.version_info[0] > 2 and isinstance(ref, bytes):
            return ref.decode()
        return ref

    def sanitize_git_path(self, path):
        dir_name = path
        split = path.split('//')
        domain = split[len(split)-1]

        if domain.endswith('.git'):
            dir_name = domain[:-4]

        return self.sanitize_directory_path(dir_name)
