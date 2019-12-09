from aws_cdk import (
    aws_iam as iam,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    core
)

from .hello_construct import Hello2Construct


class MyStack2(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        queue = sqs.Queue(
            self, "MySecondQueue",
            visibility_timeout=core.Duration.seconds(300),
        )

        topic = sns.Topic(
            self, "MySecondTopic",
            display_name="My Second Topic"
        )

        topic.add_subscription(subs.SqsSubscription(queue))

        hello = Hello2Construct(self, "MyHelloConstruct", num_buckets=4)
        user = iam.User(self, "MyUser")
        hello.grant_read(user)
