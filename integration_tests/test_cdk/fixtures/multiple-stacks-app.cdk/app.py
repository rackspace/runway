#!/usr/bin/env python3

from aws_cdk import core

from hello1.hello_stack import MyStack1
from hello2.hello_stack import MyStack2

app = core.App()
MyStack1(app, 'runway-cdk-py-sample-1')
MyStack2(app, 'runway-cdk-py-sample-2')

app.synth()
