"""'Git type Path Source."""
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .source import Source

LOGGER = logging.getLogger(__name__)


class Git(Source):
    """Git Path Source.

    The Git path source can be tasked with cloning a remote repository
    and pointing to a specific module folder (or the root).

    """

    def __init__(
        self,
        *,
        arguments: Optional[Dict[str, str]] = None,
        location: str = "",
        uri: str = "",
        **kwargs: Any,
    ) -> None:
        """Git Path Source.

        Args:
            arguments: A reference can be passed along via the arguments so that a specific
                version of the repository is cloned. **commit**, **tag**, **branch**
                are all valid keys with respective output
            location: The relative location to the root of the repository where the
                module resides. Leaving this as an empty string, ``/``, or ``./``
                will have runway look in the root folder.
            uri: The uniform resource identifier that targets the remote git repository

        """
        self.args = arguments or {}
        self.uri = uri
        self.location = location

        super().__init__(**kwargs)

    def fetch(self) -> Path:
        """Retrieve the git repository from it's remote location."""
        from git import Repo  # pylint: disable=import-outside-toplevel

        ref = self.__determine_git_ref()
        dir_name = "_".join([self.sanitize_git_path(self.uri), ref])
        cached_dir_path = self.cache_dir / dir_name

        if cached_dir_path.exists():
            return cached_dir_path

        with tempfile.TemporaryDirectory() as tmpdirname:
            tmp_repo_path = Path(tmpdirname) / dir_name
            with Repo.clone_from(self.uri, str(tmp_repo_path)) as repo:
                repo.head.reference = ref
                repo.head.reset(index=True, working_tree=True)
            shutil.move(str(tmp_repo_path), self.cache_dir)

        return cached_dir_path

    def __git_ls_remote(self, ref: str) -> str:
        """List remote repositories based on uri and ref received.

        Keyword Args:
            ref (str): The git reference value

        """
        cmd = ["git", "ls-remote", self.uri, ref]
        LOGGER.debug("getting commit ID from repo: %s", " ".join(cmd))
        ls_remote_output = subprocess.check_output(cmd)
        if b"\t" in ls_remote_output:
            commit_id = ls_remote_output.split(b"\t", maxsplit=1)[0].decode()
            LOGGER.debug("matching commit id found: %s", commit_id)
            return commit_id
        raise ValueError(f'Ref "{ref}" not found for repo {self.uri}.')

    def __determine_git_ls_remote_ref(self) -> str:
        """Determine remote ref, defaulting to HEAD unless a branch is found."""
        ref = "HEAD"
        if self.args.get("branch"):
            ref = f"refs/heads/{self.args['branch']}"
        return ref

    def __determine_git_ref(self) -> str:
        """Determine the git reference code."""
        ref_config_keys = sum(
            bool(self.args.get(i)) for i in ["commit", "tag", "branch"]
        )
        if ref_config_keys > 1:
            raise ValueError(
                "Fetching remote git sources failed: conflicting revisions "
                "(e.g. 'commit', 'tag', 'branch') specified for a package source"
            )

        if self.args.get("commit"):
            return self.args["commit"]
        if self.args.get("tag"):
            return self.args["tag"]
        return self.__git_ls_remote(self.__determine_git_ls_remote_ref())

    @classmethod
    def sanitize_git_path(cls, path: str) -> str:
        """Sanitize the git path for folder/file assignment.

        Keyword Args:
            path: The path string to be sanitized

        """
        dir_name = path
        split = path.split("//")
        domain = split[len(split) - 1]

        if domain.endswith(".git"):
            dir_name = domain[:-4]

        return cls.sanitize_directory_path(dir_name)
