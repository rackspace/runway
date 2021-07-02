"""Static site utilities."""


def add_url_scheme(url: str) -> str:
    """Add the scheme to an existing url.

    Args:
        url (str): The current url.

    """
    if url.startswith("https://") or url.startswith("http://"):
        return url
    return f"https://{url}"
