"""Test runway.utils._file_hash."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from runway.utils._file_hash import FileHash

if TYPE_CHECKING:
    from pathlib import Path

MODULE = "runway.utils._file_hash"

ALGS_TO_TEST = ["md5", "sha256"]


class TestFileHash:
    """Test FileHash."""

    @pytest.mark.parametrize("alg", ALGS_TO_TEST)
    def test_add_file(self, alg: str, tmp_path: Path) -> None:
        """Test add_file."""
        content = "hello world!"
        expected = hashlib.new(alg)
        expected.update(content.encode())
        test_file = tmp_path / "test.txt"
        test_file.write_text(content)

        result = FileHash(hashlib.new(alg))
        result.add_file(test_file)

        assert result.digest_size == expected.digest_size
        assert result.digest == expected.digest()
        assert result.hexdigest == expected.hexdigest()

    @pytest.mark.parametrize("alg", ALGS_TO_TEST)
    def test_add_file_name(self, alg: str, tmp_path: Path) -> None:
        """Test add_file_name."""
        test_file = tmp_path / "test.txt"
        test_file.resolve()
        expected = hashlib.new(alg)
        expected.update((str(test_file) + "\0").encode())

        result_path = FileHash(hashlib.new(alg))
        result_path.add_file_name(test_file)
        assert result_path.digest_size == expected.digest_size
        assert result_path.digest == expected.digest()
        assert result_path.hexdigest == expected.hexdigest()

        result_str = FileHash(hashlib.new(alg))
        result_str.add_file_name(str(test_file))
        assert result_str.digest_size == expected.digest_size
        assert result_str.digest == expected.digest()
        assert result_str.hexdigest == expected.hexdigest()

    @pytest.mark.parametrize("alg", ALGS_TO_TEST)
    def test_add_file_name_relative(self, alg: str, tmp_path: Path) -> None:
        """Test add_file_name."""
        tld = tmp_path.parents[0]
        test_file = tmp_path / "test.txt"
        test_file.resolve()
        expected = hashlib.new(alg)
        expected.update((str(test_file.relative_to(tld)) + "\0").encode())

        result_path = FileHash(hashlib.new(alg))
        result_path.add_file_name(test_file, relative_to=tld)
        assert result_path.digest_size == expected.digest_size
        assert result_path.digest == expected.digest()
        assert result_path.hexdigest == expected.hexdigest()

        result_str = FileHash(hashlib.new(alg))
        result_str.add_file_name(str(test_file), relative_to=tld)
        assert result_str.digest_size == expected.digest_size
        assert result_str.digest == expected.digest()
        assert result_str.hexdigest == expected.hexdigest()

    @pytest.mark.parametrize("alg", ALGS_TO_TEST)
    def test_add_files(self, alg: str, tmp_path: Path) -> None:
        """Test add_file."""
        content = "hello world!"
        test_file0 = tmp_path / "test0.txt"
        test_file0.write_text(content)
        test_file1 = tmp_path / "test1.txt"
        test_file1.write_text(content)

        expected = hashlib.new(alg)
        for test_file in [test_file0, test_file1]:
            expected.update((str(test_file) + "\0").encode())
            expected.update((content + "\0").encode())

        result = FileHash(hashlib.new(alg))
        result.add_files([test_file0, test_file1])

        assert result.digest_size == expected.digest_size
        assert result.digest == expected.digest()
        assert result.hexdigest == expected.hexdigest()

    @pytest.mark.parametrize("alg", ALGS_TO_TEST)
    def test_add_files_relative(self, alg: str, tmp_path: Path) -> None:
        """Test add_file."""
        tld = tmp_path.parents[0]
        content = "hello world!"
        test_file0 = tmp_path / "test0.txt"
        test_file0.write_text(content)
        test_file1 = tmp_path / "test1.txt"
        test_file1.write_text(content)

        expected = hashlib.new(alg)
        for test_file in [test_file0, test_file1]:
            expected.update((str(test_file.relative_to(tld)) + "\0").encode())
            expected.update((content + "\0").encode())

        result = FileHash(hashlib.new(alg))
        result.add_files([test_file0, test_file1], relative_to=tld)

        assert result.digest_size == expected.digest_size
        assert result.digest == expected.digest()
        assert result.hexdigest == expected.hexdigest()
