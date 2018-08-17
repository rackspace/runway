#!/usr/bin/env python
"""Module with update_api_endpoint."""
import os
import re
import subprocess
import boto3

STACK_PREFIX = 'realworld-'


def update_api_endpoint():
    """Update app environment file with backend endpoint."""
    environment = subprocess.check_output(['pipenv',
                                           'run',
                                           'runway',
                                           'whichenv']).decode().strip()
    environment_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'src',
        'environments',
        'environment.prod.ts' if environment == 'prod' else 'environment.ts'
    )
    cloudformation = boto3.resource('cloudformation')
    stack = cloudformation.Stack(STACK_PREFIX + environment)
    endpoint = [i['OutputValue'] for i in stack.outputs
                if i['OutputKey'] == 'ServiceEndpoint'][0]

    with open(environment_file, 'r') as stream:
        content = stream.read()
    content = re.sub(r'api_url: \'.*\'$',
                     "api_url: '%s/api'" % endpoint,
                     content,
                     flags=re.M)
    with open(environment_file, 'w') as stream:
        stream.write(content)


if __name__ == "__main__":
    update_api_endpoint()
