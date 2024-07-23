"""Test runway.lookups.handlers.random_string."""

from __future__ import annotations

import string
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from runway.lookups.handlers.random_string import ArgsDataModel, RandomStringLookup

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway.lookups.handlers.random_string"


class TestArgsDataModel:
    """Test ArgsDataModel."""

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = ArgsDataModel()
        assert obj.digits
        assert obj.lowercase
        assert not obj.punctuation
        assert obj.uppercase


class TestRandomStringLookup:
    """Test RandomStringLookup."""

    @pytest.mark.parametrize(
        "args, expected",
        [
            (
                {
                    "digits": False,
                    "lowercase": False,
                    "punctuation": False,
                    "uppercase": False,
                },
                "",
            ),
            (
                {
                    "digits": True,
                    "lowercase": False,
                    "punctuation": False,
                    "uppercase": False,
                },
                string.digits,
            ),
            (
                {
                    "digits": True,
                    "lowercase": True,
                    "punctuation": False,
                    "uppercase": False,
                },
                string.digits + string.ascii_lowercase,
            ),
            (
                {
                    "digits": True,
                    "lowercase": True,
                    "punctuation": True,
                    "uppercase": False,
                },
                string.digits + string.ascii_lowercase + string.punctuation,
            ),
            (
                {
                    "digits": True,
                    "lowercase": True,
                    "punctuation": True,
                    "uppercase": True,
                },
                string.digits
                + string.ascii_lowercase
                + string.punctuation
                + string.ascii_uppercase,
            ),
            (
                {
                    "digits": False,
                    "lowercase": True,
                    "punctuation": True,
                    "uppercase": True,
                },
                string.ascii_lowercase + string.punctuation + string.ascii_uppercase,
            ),
        ],
    )
    def test_calculate_char_set(self, args: object, expected: str) -> None:
        """Test calculate_char_set."""
        assert RandomStringLookup.calculate_char_set(ArgsDataModel.parse_obj(args)) == expected

    @pytest.mark.parametrize(
        "args, value, expected",
        [
            ({}, "12ab?!", False),
            ({"uppercase": False}, "12ab?!", True),
            ({}, "Abc123", True),
            ({}, "Abc", False),
            ({"digits": False}, "Abc", True),
            ({"punctuation": True}, "Abc123", False),
            ({"punctuation": True}, "12ab?!", False),
            ({"punctuation": True, "uppercase": False}, "12ab?!", True),
            ({"punctuation": True}, "12Ab?!", True),
            (
                {
                    "digits": False,
                    "lowercase": False,
                    "punctuation": False,
                    "uppercase": False,
                },
                "",
                True,
            ),
        ],
    )
    def test_ensure_has_one_of(self, args: object, expected: bool, value: str) -> None:
        """Test ensure_has_one_of."""
        assert (
            RandomStringLookup.ensure_has_one_of(ArgsDataModel.parse_obj(args), value) is expected
        )

    @pytest.mark.parametrize("length", [1, 3, 5, 7, 8, 9])
    def test_generate_random_string(self, length: int, mocker: MockerFixture) -> None:
        """Test generate_random_string."""
        char_set = "0123456789"
        choice = Mock(side_effect=list(char_set))
        mocker.patch(f"{MODULE}.secrets", choice=choice)
        assert RandomStringLookup.generate_random_string(char_set, length) == char_set[:length]
        assert choice.call_count == length
        choice.assert_called_with(char_set)

    def test_handle(self, mocker: MockerFixture) -> None:
        """Test handle."""
        args = ArgsDataModel()
        calculate_char_set = mocker.patch.object(
            RandomStringLookup, "calculate_char_set", return_value="char_set"
        )
        ensure_has_one_of = mocker.patch.object(
            RandomStringLookup, "ensure_has_one_of", return_value=True
        )
        format_results = mocker.patch.object(
            RandomStringLookup, "format_results", return_value="success"
        )
        generate_random_string = mocker.patch.object(
            RandomStringLookup, "generate_random_string", return_value="random string"
        )
        assert RandomStringLookup.handle("12", Mock()) == format_results.return_value
        calculate_char_set.assert_called_once_with(args)
        generate_random_string.assert_called_once_with(calculate_char_set.return_value, 12)
        ensure_has_one_of.assert_called_once_with(args, generate_random_string.return_value)
        format_results.assert_called_once_with(generate_random_string.return_value)

    def test_handle_digit(self, mocker: MockerFixture) -> None:
        """Test handle digit."""
        args = ArgsDataModel(lowercase=False, punctuation=False, uppercase=False)
        calculate_char_set = mocker.patch.object(
            RandomStringLookup, "calculate_char_set", return_value="char_set"
        )
        mocker.patch.object(RandomStringLookup, "ensure_has_one_of", return_value=True)
        format_results = mocker.patch.object(
            RandomStringLookup, "format_results", return_value="success"
        )
        generate_random_string = mocker.patch.object(
            RandomStringLookup, "generate_random_string", return_value="random string"
        )
        assert (
            RandomStringLookup.handle(
                "12::lowercase=false, punctuation=false, uppercase=false, transform=str",
                Mock(),
            )
            == format_results.return_value
        )
        calculate_char_set.assert_called_once_with(args)
        format_results.assert_called_once_with(
            generate_random_string.return_value,
            lowercase="false",
            punctuation="false",
            uppercase="false",
            transform="str",
        )

    def test_handle_raise_value_error(self) -> None:
        """Test handle."""
        with pytest.raises(ValueError):  # noqa: PT011
            RandomStringLookup.handle("test", Mock())

    @pytest.mark.parametrize("value, expected", [(">!?test", False), ("t3st", True)])
    def test_has_digit(self, expected: bool, value: str) -> None:
        """Test has_digit."""
        assert RandomStringLookup.has_digit(value) is expected

    @pytest.mark.parametrize("value, expected", [("TEST!", False), ("032/>,Ab", True)])
    def test_has_lowercase(self, expected: bool, value: str) -> None:
        """Test has_lowercase."""
        assert RandomStringLookup.has_lowercase(value) is expected

    @pytest.mark.parametrize("value, expected", [("Test", False), ("032/>,Ab", True)])
    def test_has_punctuation(self, expected: bool, value: str) -> None:
        """Test has_punctuation."""
        assert RandomStringLookup.has_punctuation(value) is expected

    @pytest.mark.parametrize("value, expected", [("test?!", False), ("032/>,Ab", True)])
    def test_has_uppercase(self, expected: bool, value: str) -> None:
        """Test has_uppercase."""
        assert RandomStringLookup.has_uppercase(value) is expected
