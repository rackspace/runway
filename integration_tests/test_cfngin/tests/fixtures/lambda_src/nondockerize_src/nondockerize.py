"""Test handler."""
import lib


def handler(event, context):
    """Handle lambda."""
    try:
        if lib.RESPONSE_OBJ.shape == (3, 5):
            return {
                'statusCode': 200,
                'body': str(lib.RESPONSE_OBJ.shape)
            }
        raise ValueError
    except:
        return {
            'statusCode': 500,
            'body': 'fail'
        }
