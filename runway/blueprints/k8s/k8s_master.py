#!/usr/bin/env python
"""Module with k8s cluster resources."""
from __future__ import print_function

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
    """Stacker blueprint for creating k8s cluster resources."""

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

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        variables = self.get_variables()
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
                VpcId=variables["VPC"].ref,
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
                ManagedPolicyArns=[
                    IAM_POLICY_ARN_PREFIX + i
                    for i in ["AmazonEKSClusterPolicy", "AmazonEKSServicePolicy"]
                ],
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
                Name=variables["EksClusterName"].ref,
                Version=variables["EksVersion"].ref,
                RoleArn=eksservicerole.get_att("Arn"),
                ResourcesVpcConfig=eks.ResourcesVpcConfig(
                    SecurityGroupIds=[ccpsecuritygroup.ref()],
                    SubnetIds=variables["EksSubnets"].ref,
                ),
            )
        )
        template.add_output(
            Output(
                "%sName" % ekscluster.title,
                Description="EKS Cluster Name",
                Export=Export(Sub("${AWS::StackName}-%sName" % ekscluster.title)),
                Value=ekscluster.ref(),
            )
        )
        template.add_output(
            Output(
                "%sEndpoint" % ekscluster.title,
                Description="EKS Cluster Endpoint",
                Export=Export(Sub("${AWS::StackName}-%sEndpoint" % ekscluster.title)),
                Value=ekscluster.get_att("Endpoint"),
            )
        )

        # Additional Outputs
        template.add_output(
            Output(
                "VpcId",
                Description="EKS Cluster VPC Id",
                Export=Export(Sub("${AWS::StackName}-VpcId")),
                Value=variables["VPC"].ref,
            )
        )
        template.add_output(
            Output(
                "Subnets",
                Description="EKS Cluster Subnets",
                Export=Export(Sub("${AWS::StackName}-Subnets")),
                Value=Join(",", variables["EksSubnets"].ref),
            )
        )


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from runway.cfngin.context import Context

    print(Cluster("test", Context({"namespace": "test"}), None).to_json())
