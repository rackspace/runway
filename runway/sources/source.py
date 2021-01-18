"""Abstract parent class for a 'Source' type object.

Allows us to specify specific remote sourced resources for out application
(Git, S3, ect.)

"""
import logging
from pathlib import Path
from typing import Any, Union

from ..constants import DEFAULT_CACHE_DIR

LOGGER = logging.getLogger(__name__)


class Source:
    """Abstract parent class for a 'Source' type object.

    The Source parent class allows us to specify remote resources
    for our application via services such as Git or S3.  A cache
    directory, as part of object's configuration, is automatically
    created by default: ``./.runway/cache``.
    This folder can be overridden by specifying the ``cache_dir`` property
    in the configuration passed.

    Every Source type object is expected to have a ``fetch`` method which
    will return the folder path at where the module requested resides.

    """

    cache_dir: Path

    def __init__(self, *, cache_dir: Union[Path, str] = DEFAULT_CACHE_DIR, **_: Any):
        """Source.

        Args:
            cache_dir: The directory where the given remote resource should be
                cached.

        """
        self.cache_dir = cache_dir if isinstance(cache_dir, Path) else Path(cache_dir)

        self.__create_cache_directory()

    def fetch(self) -> Path:
        """Retrieve remote source. To be implemented in each subclass."""
        raise NotImplementedError

    def __create_cache_directory(self) -> None:
        """If no cache directory exists for the remote runway modules, create one."""
        self.cache_dir.mkdir(exist_ok=True, parents=True)

    @staticmethod
    def sanitize_directory_path(uri: str) -> str:
        """Sanitize a Source directory path string.

        Arguments:
            uri: The uniform resource identifier when targetting a remote resource.

        """
        for i in ["@", "/", ":"]:
            uri = uri.replace(i, "_")
        return uri
