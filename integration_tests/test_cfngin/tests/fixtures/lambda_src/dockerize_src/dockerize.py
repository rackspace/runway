"""Test handler."""
import requests


def handler(event, context):
    """Handle lambda."""
    response = requests.get('https://api.github.com')
    print(response)
    return {
        'statusCode': 200,
        'body': 'success'
    }
