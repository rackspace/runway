"""Test runway._cli.logs."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Any

import pytest

from runway._cli.logs import (
    LOG_FIELD_STYLES,
    LOG_FORMAT,
    LOG_FORMAT_VERBOSE,
    LOG_LEVEL_STYLES,
    LogSettings,
)
from runway._logging import LogLevels

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway._cli.logs"


class TestLogSettings:
    """Test LogSettings."""

    @pytest.mark.parametrize("debug", [0, 1, 2])
    @pytest.mark.parametrize("no_color", [False, True])
    @pytest.mark.parametrize("verbose", [False, True])
    def test___init__(
        self, debug: int, no_color: bool, mocker: MockerFixture, verbose: bool
    ) -> None:
        """Test __init__."""
        env = {
            "RUNWAY_LOG_FIELD_STYLES": None,
            "RUNWAY_LOG_FORMAT": "[test] %(message)s",
            "RUNWAY_LOG_LEVEL_STYLES": None,
        }
        mocker.patch.dict(os.environ, {k: v for k, v in env.items() if v})
        obj = LogSettings(debug=debug, no_color=no_color, verbose=verbose)
        assert obj._env == {
            "field_styles": env["RUNWAY_LOG_FIELD_STYLES"],
            "fmt": env["RUNWAY_LOG_FORMAT"],
            "level_styles": env["RUNWAY_LOG_LEVEL_STYLES"],
        }
        assert obj.debug == debug
        assert obj.no_color is no_color
        assert obj.verbose is verbose

    @pytest.mark.parametrize("isatty, no_color", [(None, True), ("test-supports_colors", False)])
    def test_coloredlogs(self, isatty: str | None, mocker: MockerFixture, no_color: bool) -> None:
        """Test coloredlogs."""
        field_styles = mocker.patch.object(LogSettings, "field_styles", "test-field_styles")
        fmt = mocker.patch.object(LogSettings, "fmt", "test-fmt")
        level_styles = mocker.patch.object(LogSettings, "level_styles", "test-level_styles")
        stream = mocker.patch.object(LogSettings, "stream", "test-stream")
        mocker.patch.object(LogSettings, "supports_colors", "test-supports_colors")
        assert LogSettings(no_color=no_color).coloredlogs == {
            "field_styles": field_styles,
            "fmt": fmt,
            "isatty": isatty,
            "level_styles": level_styles,
            "stream": stream,
        }

    def test_field_styles(self) -> None:
        """Test field_styles."""
        assert LogSettings().field_styles == LOG_FIELD_STYLES

    def test_field_styles_env(self, mocker: MockerFixture) -> None:
        """Test field_styles."""
        mocker.patch.dict(os.environ, {"RUNWAY_LOG_FIELD_STYLES": "debug=red"})
        assert LogSettings().field_styles["debug"] == {"color": "red"}

    def test_field_styles_no_color(self) -> None:
        """Test field_styles."""
        assert not LogSettings(no_color=True).field_styles

    def test_fmt(self) -> None:
        """Test fmt."""
        assert LogSettings().fmt == LOG_FORMAT

    def test_fmt_env(self, mocker: MockerFixture) -> None:
        """Test fmt."""
        mocker.patch.dict(os.environ, {"RUNWAY_LOG_FORMAT": "test-format"})
        assert LogSettings().fmt == "test-format"

    def test_fmt_verbose(self, mocker: MockerFixture) -> None:
        """Test fmt."""
        mocker.patch.dict(os.environ, {"RUNWAY_LOG_FORMAT": ""})
        assert LogSettings(debug=True).fmt == LOG_FORMAT_VERBOSE
        assert LogSettings(no_color=True).fmt == LOG_FORMAT_VERBOSE
        assert LogSettings(verbose=True).fmt == LOG_FORMAT_VERBOSE

    def test_level_styles(self) -> None:
        """Test level_styles."""
        assert LogSettings().level_styles == LOG_LEVEL_STYLES

    def test_level_styles_env(self, mocker: MockerFixture) -> None:
        """Test level_styles."""
        mocker.patch.dict(os.environ, {"RUNWAY_LOG_LEVEL_STYLES": "debug=red"})
        assert LogSettings().level_styles["debug"] == {"color": "red"}

    def test_level_styles_no_color(self) -> None:
        """Test level_styles."""
        assert not LogSettings(no_color=True).level_styles

    @pytest.mark.parametrize(
        "kwargs, log_level",
        [
            ({}, LogLevels.INFO),
            ({"debug": 1}, LogLevels.DEBUG),
            ({"debug": 2, "verbose": True}, LogLevels.DEBUG),
            ({"verbose": True}, LogLevels.VERBOSE),
        ],
    )
    def test_log_level(self, kwargs: dict[str, Any], log_level: LogLevels) -> None:
        """Test log_level."""
        assert LogSettings(**kwargs).log_level == log_level

    def test_stream(self) -> None:
        """Test stream."""
        assert LogSettings().stream == sys.stdout

    def test_supports_colors(self, mocker: MockerFixture) -> None:
        """Test supports_colors."""
        mocker.patch.dict(os.environ, {"GITLAB_CI": "false"})
        str_to_bool = mocker.patch(f"{MODULE}.str_to_bool", return_value=False)
        terminal_supports_colors = mocker.patch(
            f"{MODULE}.terminal_supports_colors", return_value=True
        )
        obj = LogSettings()
        assert obj.supports_colors
        str_to_bool.assert_called_once_with("false")
        terminal_supports_colors.assert_called_once_with(obj.stream)

    def test_supports_colors_gitlab_ci(self, mocker: MockerFixture) -> None:
        """Test supports_colors GITLAB_CI is truthy."""
        mocker.patch.dict(os.environ, {"GITLAB_CI": "true"})
        str_to_bool = mocker.patch(f"{MODULE}.str_to_bool", return_value=True)
        terminal_supports_colors = mocker.patch(
            f"{MODULE}.terminal_supports_colors", return_value=False
        )
        assert LogSettings().supports_colors
        str_to_bool.assert_called_once_with("true")
        terminal_supports_colors.assert_not_called()
