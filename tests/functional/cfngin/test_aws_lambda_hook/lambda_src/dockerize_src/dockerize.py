"""Test handler."""
# flake8: noqa
# pylint: disable=unused-argument
import lib


def handler(event, context):
    """Handle lambda."""
    try:
        if lib.RESPONSE_OBJ.shape == (3, 5):
            return {"statusCode": 200, "body": str(lib.RESPONSE_OBJ.shape)}
        raise ValueError
    except:  # pylint: disable=bare-except
        return {"statusCode": 500, "body": "fail"}
