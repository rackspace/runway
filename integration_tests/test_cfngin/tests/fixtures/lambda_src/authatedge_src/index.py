"""Test handler."""
# flake8: noqa
# pylint: disable=unused-argument
import rsa


def handler(event, context):
    """Handle lambda."""
    try:
        prime = rsa.prime.getprime(4)
        if isinstance(prime, int):
            return {"statusCode": 200, "body": str(prime)}
        raise ValueError
    except:  # pylint: disable=bare-except
        return {"statusCode": 500, "body": "fail"}
