"""Test handler."""
from urllib.reuqest import urlopen, Request

def handler(event, context):
    """Handle lambda."""
    req = Request('https://api.github.com')
    with urlopen(req) as url:
        f = url.read().decode('utf8')
        print(f)
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> return proper status code in lambda test
        return {
            'statusCode': 200,
            'body': 'success'
        }
<<<<<<< HEAD
=======
>>>>>>> added in lambda hook tests
=======
>>>>>>> return proper status code in lambda test
