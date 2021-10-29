#!/usr/bin/env python
"""Module with k8s nodegroup."""
import json
import os
from typing import Any

import botocore
from troposphere import Base64, Equals, If, Not, NoValue, Output, Sub, autoscaling, ec2
from troposphere.policies import AutoScalingRollingUpdate, UpdatePolicy

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import (
    CFNNumber,
    CFNString,
    EC2ImageId,
    EC2SecurityGroupId,
    EC2SubnetIdList,
    EC2VPCId,
)


def get_valid_instance_types() -> Any:
    """Return list of instance types."""
    ec2_service_file = os.path.join(
        os.path.dirname(botocore.__file__),
        "data",
        "ec2",
        "2016-11-15",
        "service-2.json",
    )
    # This encoding needs to be explicitly called out as utf-8 on Windows
    # (or it will try cp1252 instead)
    with open(ec2_service_file, "r", encoding="utf-8") as stream:
        return json.load(stream)["shapes"]["InstanceType"]["enum"]


class NodeGroup(Blueprint):
    """CFNgin blueprint for creating k8s nodegroup."""

    VARIABLES = {
        "KeyName": {
            "type": CFNString,  # string to allow it to be unset
            "description": "(Optional) EC2 Key Pair to allow SSH "
            "access to the instances",
            "default": "",
        },
        "NodeImageId": {
            "type": EC2ImageId,
            "description": "AMI id for the node instances.",
        },
        "NodeInstanceType": {
            "type": CFNString,
            "description": "EC2 instance type for the node " "instances",
            "default": "t2.medium",
            "allowed_values": get_valid_instance_types(),
            "constraint_description": "Must be a valid EC2 " "instance type",
        },
        "NodeInstanceProfile": {
            "type": CFNString,
            "description": "Instance profile for the nodes.",
        },
        "NodeAutoScalingGroupMinSize": {
            "type": CFNNumber,
            "description": "Minimum size of Node " "Group ASG.",
            "default": 1,
        },
        "NodeAutoScalingGroupMaxSize": {
            "type": CFNNumber,
            "description": "Maximum size of Node " "Group ASG.",
            "default": 3,
        },
        "NodeVolumeSize": {
            "type": CFNNumber,
            "description": "Node volume size",
            "default": 20,
        },
        "ClusterName": {
            "type": CFNString,
            "description": "The cluster name provided when the "
            "cluster was created. If it is "
            "incorrect, nodes will not be able to "
            "join the cluster.",
        },
        "BootstrapArguments": {
            "type": CFNString,
            "description": "Arguments to pass to the "
            "bootstrap script. See "
            "files/bootstrap.sh in "
            "https://github.com/awslabs/amazon-eks-ami",
            "default": "",
        },
        "NodeGroupName": {
            "type": CFNString,
            "description": "Unique identifier for the Node " "Group.",
        },
        "ClusterControlPlaneSecurityGroup": {
            "type": EC2SecurityGroupId,
            "description": "The security " "group of the " "cluster control " "plane.",
        },
        "VpcId": {"type": EC2VPCId, "description": "The VPC of the worker instances"},
        "Subnets": {
            "type": EC2SubnetIdList,
            "description": "The subnets where workers can be " "created.",
        },
        "UseDesiredInstanceCount": {
            "type": CFNString,
            "description": "Should the initial bootstrap instance count be used?",
        },
    }

    def create_template(self) -> None:
        """Create template (main function called by CFNgin)."""
        template = self.template
        template.set_version("2010-09-09")
        template.set_description(
            "Kubernetes workers via EKS - V1.0.0 "
            "- compatible with amazon-eks-node-v23+"
        )

        # Metadata
        template.set_metadata(
            {
                "AWS::CloudFormation::Interface": {
                    "ParameterGroups": [
                        {
                            "Label": {"default": "EKS Cluster"},
                            "Parameters": [
                                self.variables[i].name
                                for i in [
                                    "ClusterName",
                                    "ClusterControlPlaneSecurityGroup",
                                ]
                            ],
                        },
                        {
                            "Label": {"default": "Worker Node Configuration"},
                            "Parameters": [
                                self.variables[i].name
                                for i in [
                                    "NodeGroupName",
                                    "NodeAutoScalingGroupMinSize",
                                    "NodeAutoScalingGroupMaxSize",
                                    "UseDesiredInstanceCount",
                                    "NodeInstanceType",
                                    "NodeInstanceProfile",
                                    "NodeImageId",
                                    "NodeVolumeSize",
                                    "KeyName",
                                    "BootstrapArguments",
                                ]
                            ],
                        },
                        {
                            "Label": {"default": "Worker Network Configuration"},
                            "Parameters": [
                                self.variables[i].name for i in ["VpcId", "Subnets"]
                            ],
                        },
                    ]
                }
            }
        )

        # Conditions
        template.add_condition(
            "DesiredInstanceCountSpecified",
            Equals(self.variables["UseDesiredInstanceCount"].ref, "true"),
        )
        template.add_condition(
            "KeyNameSpecified", Not(Equals(self.variables["KeyName"].ref, ""))
        )

        # Resources
        nodesecuritygroup = template.add_resource(
            ec2.SecurityGroup(
                "NodeSecurityGroup",
                GroupDescription="Security group for all nodes in the cluster",
                Tags=[
                    {
                        "Key": Sub("kubernetes.io/cluster/${ClusterName}"),
                        "Value": "owned",
                    },
                ],
                VpcId=self.variables["VpcId"].ref,
            )
        )
        template.add_output(
            Output(
                "NodeSecurityGroup",
                Description="Security group for all nodes in the cluster",
                Value=nodesecuritygroup.ref(),
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                "NodeSecurityGroupIngress",
                Description="Allow node to communicate with each other",
                GroupId=nodesecuritygroup.ref(),
                SourceSecurityGroupId=nodesecuritygroup.ref(),
                IpProtocol="-1",
                FromPort=0,
                ToPort=65535,
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                "NodeSecurityGroupFromControlPlaneIngress",
                Description="Allow worker Kubelets and pods to receive "
                "communication from the cluster control plane",
                GroupId=nodesecuritygroup.ref(),
                SourceSecurityGroupId=self.variables[
                    "ClusterControlPlaneSecurityGroup"
                ].ref,
                IpProtocol="tcp",
                FromPort=1025,
                ToPort=65535,
            )
        )
        template.add_resource(
            ec2.SecurityGroupEgress(
                "ControlPlaneEgressToNodeSecurityGroup",
                Description="Allow the cluster control plane to communicate "
                "with worker Kubelet and pods",
                GroupId=self.variables["ClusterControlPlaneSecurityGroup"].ref,
                DestinationSecurityGroupId=nodesecuritygroup.ref(),
                IpProtocol="tcp",
                FromPort=1025,
                ToPort=65535,
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                "NodeSecurityGroupFromControlPlaneOn443Ingress",
                Description="Allow pods running extension API servers on port "
                "443 to receive communication from cluster "
                "control plane",
                GroupId=nodesecuritygroup.ref(),
                SourceSecurityGroupId=self.variables[
                    "ClusterControlPlaneSecurityGroup"
                ].ref,  # noqa
                IpProtocol="tcp",
                FromPort=443,
                ToPort=443,
            )
        )
        template.add_resource(
            ec2.SecurityGroupEgress(
                "ControlPlaneEgressToNodeSecurityGroupOn443",
                Description="Allow the cluster control plane to communicate "
                "with pods running extension API servers on port "
                "443",
                GroupId=self.variables["ClusterControlPlaneSecurityGroup"].ref,
                DestinationSecurityGroupId=nodesecuritygroup.ref(),
                IpProtocol="tcp",
                FromPort=443,
                ToPort=443,
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                "ClusterControlPlaneSecurityGroupIngress",
                Description="Allow pods to communicate with the cluster API " "Server",
                GroupId=self.variables["ClusterControlPlaneSecurityGroup"].ref,
                SourceSecurityGroupId=nodesecuritygroup.ref(),
                IpProtocol="tcp",
                FromPort=443,
                ToPort=443,
            )
        )

        nodelaunchtemplate = template.add_resource(
            ec2.LaunchTemplate(
                "NodeLaunchTemplate",
                LaunchTemplateData=ec2.LaunchTemplateData(
                    BlockDeviceMappings=[
                        ec2.LaunchTemplateBlockDeviceMapping(
                            DeviceName="/dev/xvda",
                            Ebs=ec2.EBSBlockDevice(
                                DeleteOnTermination=True,
                                VolumeSize=self.variables["NodeVolumeSize"].ref,
                                VolumeType="gp2",
                            ),
                        ),
                    ],
                    IamInstanceProfile=ec2.IamInstanceProfile(
                        Arn=self.variables["NodeInstanceProfile"].ref
                    ),
                    ImageId=self.variables["NodeImageId"].ref,
                    InstanceType=self.variables["NodeInstanceType"].ref,
                    KeyName=If(
                        "KeyNameSpecified", self.variables["KeyName"].ref, NoValue
                    ),
                    MetadataOptions=ec2.MetadataOptions(
                        HttpPutResponseHopLimit=2,
                        HttpEndpoint="enabled",
                        HttpTokens="optional",
                    ),
                    SecurityGroupIds=[nodesecuritygroup.ref()],
                    UserData=Base64(
                        Sub(
                            "\n".join(
                                [
                                    "#!/bin/bash",
                                    "set -o xtrace",
                                    "/etc/eks/bootstrap.sh ${ClusterName} ${BootstrapArguments}",
                                    "/opt/aws/bin/cfn-signal --exit-code $? \\",
                                    "         --stack  ${AWS::StackName} \\",
                                    "         --resource NodeGroup  \\",
                                    "         --region ${AWS::Region}",
                                    "sudo yum install -y "
                                    "https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/"
                                    "latest/linux_amd64/amazon-ssm-agent.rpm",
                                    "sudo systemctl enable amazon-ssm-agent",
                                    "sudo systemctl start amazon-ssm-agent",
                                ]
                            )
                        )
                    ),
                ),
            )
        )

        template.add_resource(
            autoscaling.AutoScalingGroup(
                "NodeGroup",
                DesiredCapacity=If(
                    "DesiredInstanceCountSpecified",
                    self.variables["NodeAutoScalingGroupMaxSize"].ref,
                    NoValue,
                ),
                LaunchTemplate=autoscaling.LaunchTemplateSpecification(
                    LaunchTemplateId=nodelaunchtemplate.ref(),
                    Version=nodelaunchtemplate.get_att("LatestVersionNumber"),
                ),
                MinSize=self.variables["NodeAutoScalingGroupMinSize"].ref,
                MaxSize=self.variables["NodeAutoScalingGroupMaxSize"].ref,
                Tags=[
                    autoscaling.Tag(
                        "Name", Sub("${ClusterName}-${NodeGroupName}-Node"), True
                    ),
                    autoscaling.Tag(
                        Sub("kubernetes.io/cluster/${ClusterName}"), "owned", True
                    ),
                ],
                VPCZoneIdentifier=self.variables["Subnets"].ref,
                UpdatePolicy=UpdatePolicy(
                    AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                        MinInstancesInService="1", MaxBatchSize="1"
                    )
                ),
            )
        )


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from runway.context import CfnginContext

    print(  # noqa: T001
        NodeGroup("test", CfnginContext(parameters={"namespace": "test"})).to_json()
    )
