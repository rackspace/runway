"""Sample app."""

# ruff: noqa
from aws_cdk import core
from hello.hello_stack import MyStack

app = core.App()
MyStack(app, "runway-cdk-py-sample")

app.synth()
