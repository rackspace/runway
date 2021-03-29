"""CFNgin environment file parsing."""
from typing import Any, Dict


def parse_environment(raw_environment: str) -> Dict[str, Any]:
    """Parse environment file contents.

    Args:
        raw_environment: Environment file read into a string.

    """
    environment: Dict[str, Any] = {}
    for line in raw_environment.split("\n"):
        line = line.strip()
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
