"""Transfer config.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/transferconfig.py

"""
from __future__ import annotations

from typing import Any, ClassVar, Dict, List, NoReturn, Optional, Union

from s3transfer.manager import TransferConfig
from typing_extensions import TypedDict

from .utils import human_readable_to_bytes

# If the user does not specify any overrides,
# these are the default values we use for the s3 transfer
# commands.
TransferConfigDict = TypedDict(
    "TransferConfigDict",
    max_bandwidth=Optional[Union[int, str]],
    max_concurrent_requests=int,
    max_queue_size=int,
    multipart_chunksize=Union[int, str],
    multipart_threshold=Union[int, str],
)

DEFAULTS: TransferConfigDict = {
    "max_bandwidth": None,
    "max_concurrent_requests": 10,
    "max_queue_size": 1000,
    "multipart_chunksize": 8 * (1024 ** 2),
    "multipart_threshold": 8 * (1024 ** 2),
}


class InvalidConfigError(Exception):
    """Invalid configuration."""


class RuntimeConfig:
    """Runtime configuration."""

    POSITIVE_INTEGERS: ClassVar[List[str]] = [
        "max_bandwidth",
        "max_concurrent_requests",
        "max_queue_size",
        "multipart_chunksize",
        "multipart_threshold",
    ]
    HUMAN_READABLE_SIZES: ClassVar[List[str]] = [
        "multipart_chunksize",
        "multipart_threshold",
    ]
    HUMAN_READABLE_RATES: ClassVar[List[str]] = ["max_bandwidth"]

    @staticmethod
    def defaults() -> TransferConfigDict:
        """Return default values."""
        return DEFAULTS.copy()

    @classmethod
    def build_config(
        cls,
        *,
        max_bandwidth: Optional[Union[int, str]] = None,
        max_concurrent_requests: Optional[Union[int, str]] = None,
        max_queue_size: Optional[Union[int, str]] = None,
        multipart_chunksize: Optional[Union[int, str]] = None,
        multipart_threshold: Optional[Union[int, str]] = None,
    ) -> TransferConfigDict:
        """Create and convert a runtime config dictionary.

        This method will merge and convert S3 runtime configuration
        data into a single dictionary that can then be passed to classes
        that use this runtime config.

        """
        runtime_config = DEFAULTS.copy()
        kwargs = {
            "max_bandwidth": max_bandwidth,
            "max_concurrent_requests": max_concurrent_requests,
            "max_queue_size": max_queue_size,
            "multipart_chunksize": multipart_chunksize,
            "multipart_threshold": multipart_threshold,
        }
        runtime_config.update(  # type: ignore
            **{k: v for k, v in kwargs.items() if v is not None}
        )
        cls._convert_human_readable_sizes(runtime_config)
        cls._convert_human_readable_rates(runtime_config)
        cls._validate_config(runtime_config)
        return runtime_config

    @classmethod
    def _convert_human_readable_sizes(cls, runtime_config: TransferConfigDict) -> None:
        for attr in cls.HUMAN_READABLE_SIZES:
            value = runtime_config.get(attr)
            if isinstance(value, str):
                runtime_config[attr] = human_readable_to_bytes(value)

    @classmethod
    def _convert_human_readable_rates(cls, runtime_config: TransferConfigDict) -> None:
        for attr in cls.HUMAN_READABLE_RATES:
            value = runtime_config.get(attr)
            if isinstance(value, str):
                if not value.endswith("B/s"):
                    raise InvalidConfigError(
                        f"Invalid rate: {value}. The value must be expressed "
                        "as a rate in terms of bytes per seconds "
                        "(e.g. 10MB/s or 800KB/s)"
                    )
                runtime_config[attr] = human_readable_to_bytes(value[:-2])

    @classmethod
    def _validate_config(cls, runtime_config: TransferConfigDict) -> None:
        for attr in cls.POSITIVE_INTEGERS:
            value = runtime_config.get(attr)
            if value is not None:
                try:
                    runtime_config[attr] = int(value)
                    if not runtime_config[attr] > 0:
                        cls._error_positive_value(attr, value)
                except ValueError:
                    cls._error_positive_value(attr, value)

    @staticmethod
    def _error_positive_value(name: str, value: int) -> NoReturn:
        raise InvalidConfigError(
            f"Value for {name} must be a positive integer: {value}"
        )


def create_transfer_config_from_runtime_config(
    runtime_config: TransferConfigDict,
) -> TransferConfig:
    """Create an equivalent s3transfer TransferConfig.

    Args:
        runtime_config: A valid RuntimeConfig-generated dict.

    Returns:
        A TransferConfig with the same configuration as the runtime config.

    """
    translation_map = {
        "max_bandwidth": "max_bandwidth",
        "max_concurrent_requests": "max_request_concurrency",
        "max_queue_size": "max_request_queue_size",
        "multipart_chunksize": "multipart_chunksize",
        "multipart_threshold": "multipart_threshold",
    }
    kwargs: Dict[str, Any] = {}
    for key, value in runtime_config.items():
        if key not in translation_map:
            continue
        kwargs[translation_map[key]] = value
    return TransferConfig(**kwargs)
