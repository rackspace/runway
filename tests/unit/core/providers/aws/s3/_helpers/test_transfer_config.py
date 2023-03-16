"""Test runway.core.providers.aws.s3._helpers.transfer_config."""

from __future__ import annotations

from typing import Dict

import pytest
from s3transfer.manager import TransferConfig

from runway.core.providers.aws.s3._helpers.transfer_config import (
    DEFAULTS,
    InvalidConfigError,
    RuntimeConfig,
    create_transfer_config_from_runtime_config,
)

MODULE = "runway.core.providers.aws.s3._helpers.transfer_config"


class TestRuntimeConfig:
    """Test RuntimeConfig."""

    def test_build_config(self) -> None:
        """Test build_config."""
        assert RuntimeConfig.build_config() == DEFAULTS

    def test_build_config_human_readable_rates_converted_to_bytes(self) -> None:
        """Test build_config."""
        assert (
            RuntimeConfig.build_config(max_bandwidth="1MB/s")["max_bandwidth"]
            == 1024**2
        )

    def test_build_config_human_readable_sizes_converted_to_bytes(self) -> None:
        """Test build_config."""
        assert (
            RuntimeConfig.build_config(multipart_threshold="10MB")[
                "multipart_threshold"
            ]
            == 10 * 1024 * 1024
        )

    def test_build_config_max_bandwidth_as_bits_per_second(self) -> None:
        """Test build_config."""
        with pytest.raises(InvalidConfigError):
            RuntimeConfig.build_config(max_bandwidth="1Mb/s")

    def test_build_config_max_bandwidth_no_seconds(self) -> None:
        """Test build_config."""
        with pytest.raises(InvalidConfigError):
            RuntimeConfig.build_config(max_bandwidth="1MB")

    def test_build_config_partial_override(self) -> None:
        """Test build_config."""
        config = {
            "max_concurrent_requests": 20,
            "multipart_threshold": 64 * (1024**2),
        }
        result = RuntimeConfig.build_config(**config)
        assert result["max_concurrent_requests"] == config["max_concurrent_requests"]
        assert result["multipart_threshold"] == config["multipart_threshold"]
        assert result["max_queue_size"] == DEFAULTS["max_queue_size"]

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"max_bandwidth": "not an int"},
            {"max_concurrent_requests": "not an int"},
            {"max_queue_size": "not an int"},
        ],
    )
    def test_build_config_validates_integer_types(self, kwargs: Dict[str, str]) -> None:
        """Test build_config."""
        with pytest.raises(InvalidConfigError):
            RuntimeConfig.build_config(**kwargs)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"max_bandwidth": -10},
            {"max_concurrent_requests": -10},
            {"max_queue_size": -1},
            {"multipart_chunksize": -1},
            {"multipart_threshold": -15},
        ],
    )
    def test_build_config_validates_positive_integers(
        self, kwargs: Dict[str, str]
    ) -> None:
        """Test build_config."""
        with pytest.raises(InvalidConfigError):
            RuntimeConfig.build_config(**kwargs)

    def test_defaults(self) -> None:
        """Test defaults."""
        assert RuntimeConfig.defaults() == DEFAULTS


def test_create_transfer_config_from_runtime_config() -> None:
    """Test create_transfer_config_from_runtime_config."""
    runtime_config = {
        "invalid": 0,
        "max_bandwidth": 1024**2,
        "max_concurrent_requests": 3,
        "max_queue_size": 4,
        "multipart_chunksize": 2,
        "multipart_threshold": 1,
    }
    result = create_transfer_config_from_runtime_config(runtime_config)  # type: ignore
    assert isinstance(result, TransferConfig)
    assert result.max_bandwidth == runtime_config["max_bandwidth"]
    assert result.max_request_concurrency == runtime_config["max_concurrent_requests"]
    assert result.max_request_queue_size == runtime_config["max_queue_size"]
    assert result.multipart_chunksize == runtime_config["multipart_chunksize"]
    assert result.multipart_threshold == runtime_config["multipart_threshold"]
