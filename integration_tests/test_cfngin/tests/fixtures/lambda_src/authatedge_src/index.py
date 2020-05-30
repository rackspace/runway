"""Test handler."""
import rsa


def handler(event, context):
    """Handle lambda."""
    try:
        prime = rsa.prime.getprime(4)
        if isinstance(prime, int):
            return {
                'statusCode': 200,
                'body': str(prime)
            }
        raise ValueError
    except:
        return {
            'statusCode': 500,
            'body': 'fail'
        }
