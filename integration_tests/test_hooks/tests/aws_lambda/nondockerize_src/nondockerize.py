"""Test handler."""
from urllib.reuqest import urlopen, Request

def handler(event, context):
    """Handle lambda."""
    req = Request('https://api.github.com')
    with urlopen(req) as url:
        f = url.read().decode('utf8')
        print(f)
<<<<<<< HEAD
        return {
            'statusCode': 200,
            'body': 'success'
        }
=======
>>>>>>> added in lambda hook tests
