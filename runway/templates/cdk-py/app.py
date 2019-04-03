"""Sample app CDK module."""
from aws_cdk import aws_lambda, cdk


class SampleStack(cdk.Stack):
    """CFN stack class."""

    def __init__(self, app: cdk.App, id: str) -> None:
        """Create SampleStack."""
        super().__init__(app, id)

        with open('lambda-index.py', encoding='utf8') as stream:
            handler_code = stream.read()

        lambdaFn = aws_lambda.Function(
            self,
            'MyFunction',
            code=aws_lambda.InlineCode(handler_code),
            handler='index.main',
            timeout=300,
            runtime=aws_lambda.Runtime.PYTHON37,
        )


class App(cdk.App):
    """CDK app class."""

    def __init__(self) -> None:
        """Create App."""
        super().__init__()

        SampleStack(self, 'SampleStack')


def main() -> None:
    """Handle cli invocation."""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
