#!/usr/bin/env python
"""Module with k8s IAM resources."""
import awacs.autoscaling
import awacs.sts
from awacs.aws import Allow, PolicyDocument, Statement
from awacs.helpers.trust import make_simple_assume_policy
from troposphere import Output, iam

from runway.cfngin.blueprints.base import Blueprint

IAM_POLICY_ARN_PREFIX = "arn:aws:iam::aws:policy/"


class Iam(Blueprint):
    """CFNgin blueprint for creating k8s IAM resources."""

    def create_template(self) -> None:
        """Create template (main function called by CFNgin)."""
        template = self.template
        template.add_version("2010-09-09")
        template.add_description("Kubernetes IAM policies - V1.0.0")

        # Resources
        nodeinstancerole = template.add_resource(
            iam.Role(
                "NodeInstanceRole",
                AssumeRolePolicyDocument=make_simple_assume_policy("ec2.amazonaws.com"),
                ManagedPolicyArns=[
                    IAM_POLICY_ARN_PREFIX + i
                    for i in [
                        "AmazonEKSWorkerNodePolicy",
                        "AmazonEKS_CNI_Policy",
                        "AmazonEC2ContainerRegistryReadOnly",
                        # SSM agent not shipped ootb
                        # 'AmazonSSMManagedInstanceCore'
                    ]
                ],
            )
        )
        template.add_output(
            Output(
                "NodeInstanceRole",
                Description="The node instance role name",
                Value=nodeinstancerole.ref(),
            )
        )
        template.add_output(
            Output(
                "NodeInstanceRoleArn",
                Description="The node instance role ARN",
                Value=nodeinstancerole.get_att("Arn"),
            )
        )

        nodeinstanceprofile = template.add_resource(
            iam.InstanceProfile(
                "NodeInstanceProfile", Path="/", Roles=[nodeinstancerole.ref()]
            )
        )
        template.add_output(
            Output(
                "NodeInstanceProfile",
                Description="The node instance profile",
                Value=nodeinstanceprofile.ref(),
            )
        )
        template.add_output(
            Output(
                "NodeInstanceProfileArn",
                Description="The node instance profile ARN",
                Value=nodeinstanceprofile.get_att("Arn"),
            )
        )

        template.add_resource(
            iam.Role(
                "ClusterAutoScalerInstanceRole",
                AssumeRolePolicyDocument=make_simple_assume_policy("ec2.amazonaws.com"),
                Policies=[
                    iam.Policy(
                        PolicyName="cluster-autoscaler",
                        PolicyDocument=PolicyDocument(
                            Version="2012-10-17",
                            Statement=[
                                Statement(
                                    Action=[
                                        awacs.autoscaling.DescribeAutoScalingGroups,
                                        awacs.autoscaling.DescribeAutoScalingInstances,
                                        awacs.autoscaling.DescribeTags,
                                        awacs.autoscaling.SetDesiredCapacity,
                                        awacs.autoscaling.TerminateInstanceInAutoScalingGroup,
                                    ],
                                    Effect=Allow,
                                    Resource=["*"],
                                )
                            ],
                        ),
                    )
                ],
            )
        )


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from runway.context import CfnginContext

    print(  # noqa: T001
        Iam("test", CfnginContext(parameters={"namespace": "test"})).to_json()
    )
