"""CFNgin environment file parsing."""

from typing import Any


def parse_environment(raw_environment: str) -> dict[str, Any]:
    """Parse environment file contents.

    Args:
        raw_environment: Environment file read into a string.

    """
    environment: dict[str, Any] = {}
    for raw_line in raw_environment.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#"):
            continue

        try:
            key, value = line.split(":", 1)
        except ValueError:
            raise ValueError("Environment must be in key: value format") from None

        environment[key] = value.strip()
    return environment
