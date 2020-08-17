"""Add all configured (CloudFront compatable) headers to origin response."""
from shared import as_cloud_front_headers, get_config  # pylint: disable=import-error

CONFIG = get_config()


def handler(event, _context):
    """Handle adding the headers to the origin response.

    Args:
        event (Any): The Lambda Event.
        _context (Any): Lambda context object.

    """
    headers = CONFIG.get("http_headers")
    # Format to be CloudFront compatable
    configured_headers = as_cloud_front_headers(headers)
    response = event["Records"][0]["cf"]["response"]
    response["headers"].update(configured_headers)
    return response
