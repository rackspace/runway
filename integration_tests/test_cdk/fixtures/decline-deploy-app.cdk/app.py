#!/usr/bin/env python3
"""Sample app."""
from aws_cdk import core
from hello.hello_stack import MyStack

app = core.App()
MyStack(app, "runway-cdk-py-sample")

app.synth()
