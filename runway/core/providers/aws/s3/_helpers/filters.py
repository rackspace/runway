"""File filter.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/filters.py

"""
from __future__ import annotations

import fnmatch
import logging
import os
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Generator,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    cast,
)

from typing_extensions import Literal

from .utils import split_s3_bucket_key

if TYPE_CHECKING:
    from .file_generator import FileStats
    from .parameters import ParametersDataModel

LOGGER = logging.getLogger(__name__.replace("._", "."))


_FilterType = Literal["exclude", "include"]
FileStatus = NamedTuple("FileStatus", [("file_stats", "FileStats"), ("include", bool)])
FilterPattern = NamedTuple("FilterPattern", [("type", _FilterType), ("pattern", str)])


class Filter:
    """Universal exclude/include filter."""

    FILTER_TYPES: ClassVar[Tuple[_FilterType, ...]] = (
        "exclude",
        "include",
    )

    def __init__(
        self,
        patterns: Iterable[FilterPattern],
        src_rootdir: Optional[str],
        dest_rootdir: Optional[str],
    ) -> None:
        """Instantiate class.

        Args:
            patterns: List of filter patterns.
            src_rootdir: The source root directory where the patterns are
                evaluated.
            dest_rootdir: The destination root directory where the patterns are
                evaluated.

        """
        self._original_patterns = patterns
        self.patterns = self._full_path_patterns(patterns, src_rootdir)
        self.dest_patterns = self._full_path_patterns(patterns, dest_rootdir)

    @staticmethod
    def _full_path_patterns(
        patterns: Iterable[FilterPattern], rootdir: Optional[str]
    ) -> List[FilterPattern]:
        """Prefix each pattern with the root directory.

        Args:
            patterns: List of filter patterns.
            rootdir: The root directory to add to each pattern.

        """
        if rootdir:
            return sorted(  # sort for consistency
                [
                    FilterPattern(type=f.type, pattern=os.path.join(rootdir, f.pattern))
                    for f in patterns
                ]
            )
        return list(patterns)

    def call(self, files: Iterator[FileStats]) -> Generator[FileStats, None, None]:
        """Iterate over the yielded FileStats objects.

        Determines the type of the file and applies pattern matching to
        determine if the rule applies. While iterating though the patterns the
        file is assigned a boolean flag to determine if a file should be
        yielded on past the filer. Anything identified by the exclude filter
        has its flag set to false. Anything identified by the include filter
        has its flag set to True. All files begin with the flag set to true.
        Rules listed at the end will overwrite flags thrown by rules listed
        before it.

        """
        for file_stats in files:
            file_status = FileStatus(file_stats, True)
            for src_fp, dest_fp in zip(self.patterns, self.dest_patterns):
                current_file_status = self._match_pattern(src_fp, file_stats)
                if current_file_status is not None:
                    file_status = current_file_status
                dst_current_file_status = self._match_pattern(dest_fp, file_stats)
                if dst_current_file_status is not None:
                    file_status = dst_current_file_status
            LOGGER.debug(
                "=%s final filtered status, should_include: %s",
                file_stats.src,
                file_status.include,
            )
            if file_status.include:
                yield file_stats

    @staticmethod
    def _match_pattern(
        filter_pattern: FilterPattern, file_stats: FileStats
    ) -> Optional[FileStatus]:
        """Match file to pattern.

        Args:
            filter_pattern: Filter pattern to run against file.
            file_stats: Information about a file.

        """
        file_status = None
        if file_stats.src_type == "local":
            path_pattern = filter_pattern.pattern.replace("/", os.sep)
        else:
            path_pattern = filter_pattern.pattern.replace(os.sep, "/")
        is_match = fnmatch.fnmatch(str(file_stats.src), path_pattern)
        if is_match and filter_pattern.type == "include":
            file_status = FileStatus(file_stats, True)
            LOGGER.debug("%s matched include filter: %s", file_stats.src, path_pattern)
        elif is_match and filter_pattern.type == "exclude":
            file_status = FileStatus(file_stats, False)
            LOGGER.debug("%s matched exclude filter: %s", file_stats.src, path_pattern)
        else:
            LOGGER.debug(
                "%s did not match %s filter: %s",
                file_stats.src,
                filter_pattern.type,
                path_pattern,
            )
        return file_status

    @classmethod
    def parse_params(cls, parameters: ParametersDataModel) -> Filter:
        """Parse parameters to create a Filter instance."""
        if not (parameters.exclude or parameters.include):
            return Filter([], None, None)
        filter_patterns: Set[FilterPattern] = set()
        for filter_type in cls.FILTER_TYPES:
            for pat in parameters[filter_type]:
                filter_patterns.add(
                    FilterPattern(type=cast(_FilterType, filter_type), pattern=pat)
                )
        return Filter(
            filter_patterns,
            cls.parse_rootdir(parameters.src),
            cls.parse_rootdir(parameters.dest),
        )

    @classmethod
    def parse_rootdir(cls, path: str, dir_op: bool = True) -> str:
        """Parse path to extract the root directory.

        Args:
            path: Path to parse.
            dir_op: If the path is a directory.

        """
        if path.startswith("s3://"):
            return cls._parse_rootdir_s3(path, dir_op)
        return cls._parse_rootdir_local(path, dir_op)

    @staticmethod
    def _parse_rootdir_local(path: str, dir_op: bool = True) -> str:
        """Get root directory from local path.

        Args:
            path: Path to parse.
            dir_op: If the path is a directory.

        """
        if dir_op:
            return os.path.abspath(path)
        return os.path.abspath(os.path.dirname(path))

    @staticmethod
    def _parse_rootdir_s3(path: str, dir_op: bool = True) -> str:
        """Get root directory from S3 path.

        Args:
            path: Path to parse.
            dir_op: If the path is a directory.

        """
        bucket, key = split_s3_bucket_key(path)
        if not (dir_op or key.endswith("/")):
            key = "/".join(key.split("/")[:-1])
        return "/".join([bucket, key])
