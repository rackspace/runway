#!/usr/bin/env python
"""Module with update_api_endpoint."""

import os
import re
import subprocess

import boto3

STACK_PREFIX = "realworld-"


def update_api_endpoint() -> None:
    """Update app environment file with backend endpoint."""
    environment = subprocess.check_output(["poetry", "run", "runway", "whichenv"]).decode().strip()
    environment_file = os.path.join(  # noqa: PTH118
        os.path.dirname(os.path.realpath(__file__)),  # noqa: PTH120
        "src",
        "environments",
        "environment.prod.ts" if environment == "prod" else "environment.ts",
    )
    cloudformation = boto3.resource("cloudformation")
    stack = cloudformation.Stack(STACK_PREFIX + environment)
    endpoint = next(i["OutputValue"] for i in stack.outputs if i["OutputKey"] == "ServiceEndpoint")

    with open(environment_file) as stream:  # noqa: PTH123
        content = stream.read()
    content = re.sub(r"api_url: \'.*\'$", f"api_url: '{endpoint}/api'", content, flags=re.MULTILINE)
    with open(environment_file, "w") as stream:  # noqa: PTH123
        stream.write(content)


if __name__ == "__main__":
    update_api_endpoint()
