"""Test runway.core.providers.aws.s3._helpers.comparator."""

from __future__ import annotations

import datetime
from typing import List, Optional

import pytest
from mock import Mock

from runway.core.providers.aws.s3._helpers.comparator import Comparator
from runway.core.providers.aws.s3._helpers.file_generator import FileStats

MODULE = "runway.core.providers.aws.s3._helpers.comparator"

NOW = datetime.datetime.now()


class TestComparator:
    """Test Comparator."""

    comparator: Comparator
    not_at_dest_sync_strategy: Mock
    not_at_src_sync_strategy: Mock
    sync_strategy: Mock

    def setup_method(self) -> None:
        """Run before each test method if run to return the class instance attrs to default."""
        self.not_at_dest_sync_strategy = Mock()
        self.not_at_src_sync_strategy = Mock()
        self.sync_strategy = Mock()
        self.comparator = Comparator(
            self.sync_strategy,
            self.not_at_dest_sync_strategy,
            self.not_at_src_sync_strategy,
        )

    def test_call_compare_key_equal_should_not_sync(self) -> None:
        """Test call compare key equal should not sync."""
        self.sync_strategy.determine_should_sync.return_value = False
        ref_list: List[FileStats] = []
        result_list: List[FileStats] = []
        src_files = [
            FileStats(
                src="",
                dest="",
                compare_key="comparator_test.py",
                size=10,
                last_update=NOW,
                src_type="local",
                dest_type="s3",
                operation_name="upload",
            )
        ]
        dest_files = [
            FileStats(
                src="",
                dest="",
                compare_key="comparator_test.py",
                size=10,
                last_update=NOW,
                src_type="s3",
                dest_type="local",
                operation_name="",
            )
        ]
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

        # Try when the sync strategy says to sync the file.
        self.sync_strategy.determine_should_sync.return_value = True
        ref_list = []
        result_list = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        ref_list.append(src_files[0])
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

    def test_call_compare_key_greater(self):
        """Test call compare key greater."""
        self.not_at_dest_sync_strategy.determine_should_sync.return_value = False
        self.not_at_src_sync_strategy.determine_should_sync.return_value = True

        src_files: List[FileStats] = []
        dest_files: List[FileStats] = []
        ref_list: List[FileStats] = []
        result_list: List[FileStats] = []
        src_file = FileStats(
            src="",
            dest="",
            compare_key="domparator_test.py",
            size=10,
            last_update=NOW,
            src_type="local",
            dest_type="s3",
            operation_name="upload",
        )
        dest_file = FileStats(
            src="",
            dest="",
            compare_key="comparator_test.py",
            size=10,
            last_update=NOW,
            src_type="s3",
            dest_type="local",
            operation_name="",
        )
        src_files.append(src_file)
        dest_files.append(dest_file)
        ref_list.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

        # Now try when the sync strategy says not to sync the file.
        self.not_at_src_sync_strategy.determine_should_sync.return_value = False
        result_list = []
        ref_list = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

    def test_call_compare_key_less(self) -> None:
        """Test call compare key less."""
        self.not_at_src_sync_strategy.determine_should_sync.return_value = False
        self.not_at_dest_sync_strategy.determine_should_sync.return_value = True
        ref_list: List[FileStats] = []
        result_list: List[FileStats] = []
        src_files: List[FileStats] = []
        dest_files: List[FileStats] = []
        src_file = FileStats(
            src="",
            dest="",
            compare_key="bomparator_test.py",
            size=10,
            last_update=NOW,
            src_type="local",
            dest_type="s3",
            operation_name="upload",
        )
        dest_file = FileStats(
            src="",
            dest="",
            compare_key="comparator_test.py",
            size=10,
            last_update=NOW,
            src_type="s3",
            dest_type="local",
            operation_name="",
        )
        src_files.append(src_file)
        dest_files.append(dest_file)
        ref_list.append(src_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

        # Now try when the sync strategy says not to sync the file.
        self.not_at_dest_sync_strategy.determine_should_sync.return_value = False
        result_list = []
        ref_list = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

    def test_call_empty_dest(self) -> None:
        """Test call empty dest."""
        self.not_at_dest_sync_strategy.determine_should_sync.return_value = True
        src_files: List[FileStats] = []
        dest_files: List[FileStats] = []
        ref_list: List[FileStats] = []
        result_list: List[FileStats] = []
        src_file = FileStats(
            src="",
            dest="",
            compare_key="domparator_test.py",
            size=10,
            last_update=NOW,
            src_type="local",
            dest_type="s3",
            operation_name="upload",
        )
        src_files.append(src_file)
        ref_list.append(src_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

        # Now try when the sync strategy says not to sync the file.
        self.not_at_dest_sync_strategy.determine_should_sync.return_value = False
        result_list = []
        ref_list = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

    def test_call_empty_src(self) -> None:
        """Test call empty src."""
        self.not_at_src_sync_strategy.determine_should_sync.return_value = True
        src_files: List[FileStats] = []
        dest_files: List[FileStats] = []
        ref_list: List[FileStats] = []
        result_list: List[FileStats] = []
        dest_file = FileStats(
            src="",
            dest="",
            compare_key="comparator_test.py",
            size=10,
            last_update=NOW,
            src_type="s3",
            dest_type="local",
            operation_name="",
        )
        dest_files.append(dest_file)
        ref_list.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

        # Now try when the sync strategy says not to sync the file.
        self.not_at_src_sync_strategy.determine_should_sync.return_value = False
        result_list = []
        ref_list = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

    def test_call_empty_src_dest(self) -> None:
        """Test call."""
        src_files: List[FileStats] = []
        dest_files: List[FileStats] = []
        ref_list: List[FileStats] = []
        result_list: List[FileStats] = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        assert result_list == ref_list

    @pytest.mark.parametrize(
        "src_file, dest_file, expected",
        [
            (None, None, "equal"),
            (None, Mock(compare_key=""), "equal"),
            (Mock(compare_key=""), None, "equal"),
            (Mock(compare_key=""), Mock(compare_key=""), "equal"),
            (Mock(compare_key="tes"), Mock(compare_key="test"), "less_than"),
            (Mock(compare_key="test"), Mock(compare_key="tes"), "greater_than"),
        ],
    )
    def test_compare_comp_key(
        self,
        dest_file: Optional[FileStats],
        expected: str,
        src_file: Optional[FileStats],
    ) -> None:
        """Test compare_comp_key."""
        assert Comparator.compare_comp_key(src_file, dest_file) == expected
