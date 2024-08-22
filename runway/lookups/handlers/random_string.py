"""Generate a random string."""

from __future__ import annotations

import logging
import secrets
import string
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from ...utils import BaseModel
from .base import LookupHandler

if TYPE_CHECKING:
    from collections.abc import Sequence


LOGGER = logging.getLogger(__name__)


class ArgsDataModel(BaseModel):
    """Arguments data model."""

    digits: bool = True
    lowercase: bool = True
    punctuation: bool = False
    uppercase: bool = True


class RandomStringLookup(LookupHandler[Any]):
    """Random string lookup."""

    TYPE_NAME: ClassVar[str] = "random.string"
    """Name that the Lookup is registered as."""

    @staticmethod
    def calculate_char_set(args: ArgsDataModel) -> str:
        """Calculate character set from the provided arguments."""
        char_set = ""
        if args.digits:
            char_set += string.digits
        if args.lowercase:
            char_set += string.ascii_lowercase
        if args.punctuation:
            char_set += string.punctuation
        if args.uppercase:
            char_set += string.ascii_uppercase
        LOGGER.debug("character set: %s", char_set)
        return char_set

    @staticmethod
    def generate_random_string(char_set: Sequence[str], length: int) -> str:
        """Generate a random string of a set length from a set of characters."""
        return "".join(secrets.choice(char_set) for _ in range(length))

    @staticmethod
    def has_digit(value: str) -> bool:
        """Check if value contains a digit."""
        return any(v.isdigit() for v in value)

    @staticmethod
    def has_lowercase(value: str) -> bool:
        """Check if value contains lowercase."""
        return any(v.islower() for v in value)

    @staticmethod
    def has_punctuation(value: str) -> bool:
        """Check if value contains uppercase."""
        return any(v in string.punctuation for v in value)

    @staticmethod
    def has_uppercase(value: str) -> bool:
        """Check if value contains uppercase."""
        return any(v.isupper() for v in value)

    @classmethod
    def ensure_has_one_of(cls, args: ArgsDataModel, value: str) -> bool:
        """Ensure value has at least one of each required character.

        Args:
            args: Hook args.
            value: Value to check.

        """
        checks: list[Callable[[str], bool]] = []
        if args.digits:
            checks.append(cls.has_digit)
        if args.lowercase:
            checks.append(cls.has_lowercase)
        if args.punctuation:
            checks.append(cls.has_punctuation)
        if args.uppercase:
            checks.append(cls.has_uppercase)
        return sum(c(value) for c in checks) == len(checks)

    @classmethod
    def handle(cls, value: str, *_args: Any, **_kwargs: Any) -> Any:
        """Generate a random string.

        Args:
            value: The value passed to the Lookup.

        Raises:
            ValueError: Unable to find a value for the provided query and
                a default value was not provided.

        """
        raw_length, raw_args = cls.parse(value)
        length = int(raw_length)
        args = ArgsDataModel.model_validate(raw_args)
        char_set = cls.calculate_char_set(args)
        while True:
            result = cls.generate_random_string(char_set, length)
            if cls.ensure_has_one_of(args, result):
                break
        return cls.format_results(result, **raw_args)
