"""CFNgin environment file parsing."""


def parse_environment(raw_environment):
    """Parse environment file contents.

    Args:
        raw_environment (str): Environment file read into a string.

    Returns:
        Dict[str, Any]

    """
    environment = {}
    for line in raw_environment.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("#"):
            continue

        try:
            key, value = line.split(":", 1)
        except ValueError:
            raise ValueError("Environment must be in key: value format")

        environment[key] = value.strip()
    return environment
