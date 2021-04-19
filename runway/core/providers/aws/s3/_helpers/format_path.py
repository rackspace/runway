"""Format path.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/fileformat.py

"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from typing_extensions import Literal, TypedDict

SupportedPathType = Literal["local", "s3"]
FormatedPathDetails = TypedDict("FormatedPathDetails", path=str, type=SupportedPathType)
FormatPathResult = TypedDict(
    "FormatedPaths",
    dest=FormatedPathDetails,
    dir_op=bool,
    src=FormatedPathDetails,
    use_src_name=bool,
)


class FormatPath:
    """Path format base class."""

    @classmethod
    def format(cls, src: str, dest: str) -> FormatPathResult:
        """Format the source and destination for use in the file factory."""
        src_type, src_path = cls.identify_path_type(src)
        dest_type, dest_path = cls.identify_path_type(dest)
        format_table = {"s3": cls.format_s3_path, "local": cls.format_local_path}

        src_path = format_table[src_type](src_path)[0]
        dest_path, use_src_name = format_table[dest_type](dest_path)

        return {
            "dest": {"path": dest_path, "type": dest_type},
            "dir_op": True,
            "src": {"path": src_path, "type": src_type},
            "use_src_name": use_src_name,
        }

    @staticmethod
    def format_local_path(path: str, dir_op: bool = True) -> Tuple[str, bool]:
        """Format the path of local files.

        Returns whether the destination will keep its own name or take the
        source's name along with the editted path.

        Formatting Rules:
            1. If a destination file is taking on a source name, it must end
               with the appropriate operating system seperator

        General Options:
            1. If the operation is on a directory, the destination file will
               always use the name of the corresponding source file.
            2. If the path of the destination exists and is a directory it
               will always use the name of the source file.
            3. If the destination path ends with the appropriate operating
               system seperator but is not an existing directory, the
               appropriate directories will be made and the file will use the
               source's name.
            4. If the destination path does not end with the appropriate
               operating system seperator and is not an existing directory, the
               appropriate directories will be created and the file name will
               be of the one provided.

        """
        full_path = Path(path).resolve()
        if full_path.is_dir() or dir_op:
            return f"{full_path}{os.sep}", True
        if path.endswith(os.sep):
            return f"{full_path}{os.sep}", True
        return str(full_path), False

    @staticmethod
    def format_s3_path(path: str, dir_op: bool = True) -> Tuple[str, bool]:
        """Format the path of S3 files.

        Returns whether the destination will keep its own name or take the
        source's name along with the edited path.

        Formatting Rules:
            1. If a destination file is taking on a source name, it must end
               with a forward slash.

        General Options:
            1. If the operation is on objects under a common prefix,
               the destination file will always use the name of the
               corresponding source file.
            2. If the path ends with a forward slash, the appropriate prefixes
               will be formed and will use the name of the source.
            3. If the path does not end with a forward slash, the appropriate
               prefix will be formed but use the the name provided as opposed
               to the source name.

        """
        if dir_op:
            if not path.endswith("/"):
                path += "/"
            return path, True
        if path.endswith("/"):
            return path, True
        return path, False

    @staticmethod
    def identify_path_type(path: str) -> Tuple[SupportedPathType, str]:
        """Parse path.

        Args:
            path: Path to identify.

        Returns:
            Path type & raw path that has been resolved and/or stripped of prefix.

        """
        if path.startswith("s3://"):
            return "s3", path[5:]
        return "local", path
