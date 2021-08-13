"""Calculate the hash of files."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Iterable, Optional

if TYPE_CHECKING:
    import hashlib

    from _typeshed import StrPath


class FileHash:
    """Wrapper for hashlib to easily calculate file hashes.

    Attributes:
        DEFAULT_CHUNK_SIZE: Default chunk size if not defined.

    Note:
        Does not support algorithms with variable length digests (e.g. SHAKE).

    """

    DEFAULT_CHUNK_SIZE: ClassVar[int] = (
        1024 * 10_000_000  # 10mb - number of bytes in each read operation
    )

    def __init__(
        self, hash_alg: "hashlib._Hash", *, chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> None:
        """Instantiate class.

        Args:
            hash_alg: Instance of a hashlib algorithm.
            chunk_size: When reading a file, it will be read this many bytes at
                a time. Larger values are more time efficient while smaller
                values or more memory efficient.

        """
        self._hash = hash_alg  # protected to discourage direct access
        self.chunk_size = chunk_size

    @property
    def digest(self) -> bytes:
        """Digest of the data hashed so far.

        Returns:
            This is a bytes object of size ``digest_size`` which may contain
            bytes in the whole range from 0 to 255.

        """
        return self._hash.digest()

    @property
    def digest_size(self) -> int:
        """Size of the resulting hash in bytes."""
        return self._hash.digest_size

    @property
    def hexdigest(self) -> str:
        """Digest of the data hashed so far.

        Returns:
            String object that is double the length of ``digest`` and contains
            only hexadecimal digits.

        """
        return self._hash.hexdigest()

    def add_file(self, file_path: StrPath) -> None:
        """Add file contents to the hash.

        Args:
            file_path: Path of the file to add.

        """
        with open(file_path, "rb") as stream:
            # python 3.7 compatable version of `while chunk := buf.read(read_size):`
            chunk = stream.read(self.chunk_size)  # seed chunk with initial value
            while chunk:
                self._hash.update(chunk)
                chunk = stream.read(self.chunk_size)  # read in new chunk

    def add_file_name(
        self,
        file_path: StrPath,
        *,
        end_character: str = "\0",
        relative_to: Optional[StrPath] = None,
    ) -> None:
        """Add file name to the hash. This includes the path.

        Args:
            file_path: Path of the file to add. The full path (or relative) is
                included when adding it to the hash. This is not resolved prior
                to use. It is used as-is unless another argument acts up it.
            end_character: Character that will be added to the end of the file_path.
                This can be an empty string.
            relative_to: Optionally, convert the file_path to path relative to
                this one. It is recommended that both paths be absolute.

        """
        self._hash.update(
            (
                str(
                    Path(file_path).relative_to(relative_to)
                    if relative_to
                    else Path(file_path)
                )
                + end_character
            ).encode()
        )

    def add_files(
        self,
        file_paths: Iterable[StrPath],
        *,
        relative_to: Optional[StrPath] = None,
    ) -> None:
        """Add files to the hash.

        Args:
            file_paths: Paths of the files to add. The full path (or relative) is
                included when adding it to the hash. This is not resolved prior
                to use. It is used as-is unless another argument acts up it.
            relative_to: Optionally, convert the file_path to path relative to
                this one. It is recommended that both paths be absolute.

        """
        for fp in file_paths:
            self.add_file_name(fp, relative_to=relative_to)
            self.add_file(fp)
            # end of file contents; only necessary with multiple files
            self._hash.update("\0".encode())
