#!/usr/bin/env python
"""Module with k8s cluster resources."""
import awacs.iam
from awacs.aws import StringLike  # pylint: disable=no-name-in-module
from awacs.aws import Allow, Condition, PolicyDocument, Statement
from awacs.helpers.trust import make_simple_assume_policy
from troposphere import Export, Join, Output, Sub, ec2, eks, iam

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import (
    CFNString,
    EC2SubnetIdList,
    EC2VPCId,
)

IAM_POLICY_ARN_PREFIX = "arn:aws:iam::aws:policy/"


class Cluster(Blueprint):
    """CFNgin blueprint for creating k8s cluster resources."""

    VARIABLES = {
        "EksClusterName": {
            "type": CFNString,
            "description": "Name of the Kubernetes cluster",
            "min_length": 2,
            "max_length": 40,
        },
        "EksSubnets": {
            "type": EC2SubnetIdList,
            "description": "Subnets where the Kubernetes cluster " "will live",
        },
        "EksVersion": {"type": CFNString, "description": "Kubernetes version"},
        "VPC": {
            "type": EC2VPCId,
            "description": "VPC where the Kubernetes cluster will live",
        },
    }

    def create_template(self) -> None:
        """Create template (main function called by CFNgin)."""
        template = self.template
        template.add_version("2010-09-09")
        template.add_description("Kubernetes Master via EKS - V1.0.0")

        # Resources
        ccpsecuritygroup = template.add_resource(
            ec2.SecurityGroup(
                "ClusterControlPlaneSecurityGroup",
                GroupDescription="Cluster communication with worker nodes",
                Tags=[
                    {
                        "Key": Sub("kubernetes.io/cluster/${EksClusterName}"),
                        "Value": "owned",
                    },
                    {"Key": "Product", "Value": "Kubernetes"},
                    {"Key": "Project", "Value": "eks"},
                    {"Key": "Name", "Value": Sub("${EksClusterName}-sg-worker-nodes")},
                ],
                VpcId=self.variables["VPC"].ref,
            )
        )
        template.add_output(
            Output(
                ccpsecuritygroup.title,
                Description="Cluster communication with worker nodes",
                Export=Export(Sub("${AWS::StackName}-ControlPlaneSecurityGroup")),
                Value=ccpsecuritygroup.ref(),
            )
        )

        eksservicerole = template.add_resource(
            iam.Role(
                "EksServiceRole",
                AssumeRolePolicyDocument=make_simple_assume_policy("eks.amazonaws.com"),
                ManagedPolicyArns=[IAM_POLICY_ARN_PREFIX + "AmazonEKSClusterPolicy"],
                Policies=[
                    iam.Policy(
                        PolicyName="EksServiceRolePolicy",
                        PolicyDocument=PolicyDocument(
                            Statement=[
                                Statement(
                                    Action=[
                                        awacs.iam.CreateServiceLinkedRole,
                                        awacs.iam.PutRolePolicy,
                                    ],
                                    Condition=Condition(
                                        StringLike(
                                            "iam:AWSServiceName",
                                            "elasticloadbalancing.amazonaws.com",
                                        )
                                    ),
                                    Effect=Allow,
                                    Resource=[
                                        Sub(
                                            "arn:aws:iam::${AWS::AccountId}:role/"
                                            "aws-service-role/"
                                            "elasticloadbalancing.amazonaws.com/"
                                            "AWSServiceRoleForElasticLoadBalancing*"
                                        )
                                    ],
                                )
                            ]
                        ),
                    )
                ],
            )
        )

        ekscluster = template.add_resource(
            eks.Cluster(
                "EksCluster",
                Name=self.variables["EksClusterName"].ref,
                Version=self.variables["EksVersion"].ref,
                RoleArn=eksservicerole.get_att("Arn"),
                ResourcesVpcConfig=eks.ResourcesVpcConfig(
                    SecurityGroupIds=[ccpsecuritygroup.ref()],
                    SubnetIds=self.variables["EksSubnets"].ref,
                ),
            )
        )
        template.add_output(
            Output(
                f"{ekscluster.title}Name",
                Description="EKS Cluster Name",
                Export=Export(Sub(f"${{AWS::StackName}}-{ekscluster.title}Name")),
                Value=ekscluster.ref(),
            )
        )
        template.add_output(
            Output(
                f"{ekscluster.title}Endpoint",
                Description="EKS Cluster Endpoint",
                Export=Export(Sub(f"${{AWS::StackName}}-{ekscluster.title}Endpoint")),
                Value=ekscluster.get_att("Endpoint"),
            )
        )

        # Additional Outputs
        template.add_output(
            Output(
                "VpcId",
                Description="EKS Cluster VPC Id",
                Export=Export(Sub("${AWS::StackName}-VpcId")),
                Value=self.variables["VPC"].ref,
            )
        )
        template.add_output(
            Output(
                "Subnets",
                Description="EKS Cluster Subnets",
                Export=Export(Sub("${AWS::StackName}-Subnets")),
                Value=Join(",", self.variables["EksSubnets"].ref),
            )
        )


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from runway.context import CfnginContext

    print(  # noqa: T001
        Cluster("test", CfnginContext(parameters={"namespace": "test"})).to_json()
    )
