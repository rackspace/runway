#!/usr/bin/env python
"""Module with k8s nodegroup."""
from __future__ import print_function

import json
import os
import sys

from troposphere import (
    Base64, Equals, If, NoValue, Not, Output, Sub, autoscaling, ec2
)
from troposphere.policies import AutoScalingRollingUpdate, UpdatePolicy

import botocore

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import (
    CFNNumber, CFNString, EC2ImageId, EC2SecurityGroupId, EC2SubnetIdList,
    EC2VPCId
)


def get_valid_instance_types():
    """Return list of instance types."""
    ec2_service_file = os.path.join(os.path.dirname(botocore.__file__),
                                    'data',
                                    'ec2',
                                    '2016-11-15',
                                    'service-2.json')
    # This encoding needs to be explicitly called out as utf-8 on Windows
    # (or it will try cp1252 instead)
    openkwargs = {}
    if sys.version_info[0] > 2:
        openkwargs['encoding'] = 'utf-8'
    with open(ec2_service_file, 'r', **openkwargs) as stream:
        return json.load(stream)['shapes']['InstanceType']['enum']


class NodeGroup(Blueprint):
    """Stacker blueprint for creating k8s nodegroup."""

    VARIABLES = {
        'KeyName': {'type': CFNString,  # string to allow it to be unset
                    'description': '(Optional) EC2 Key Pair to allow SSH '
                                   'access to the instances',
                    'default': ''},
        'NodeImageId': {'type': EC2ImageId,
                        'description': 'AMI id for the node instances.'},
        'NodeInstanceType': {'type': CFNString,
                             'description': 'EC2 instance type for the node '
                                            'instances',
                             'default': 't2.medium',
                             'allowed_values': get_valid_instance_types(),
                             'constraint_description': 'Must be a valid EC2 '
                                                       'instance type'},
        'NodeInstanceProfile': {'type': CFNString,
                                'description': 'Instance profile for the '
                                               'nodes.'},
        'NodeAutoScalingGroupMinSize': {'type': CFNNumber,
                                        'description': 'Minimum size of Node '
                                                       'Group ASG.',
                                        'default': 1},
        'NodeAutoScalingGroupMaxSize': {'type': CFNNumber,
                                        'description': 'Maximum size of Node '
                                                       'Group ASG.',
                                        'default': 3},
        'NodeVolumeSize': {'type': CFNNumber,
                           'description': 'Node volume size',
                           'default': 20},
        'ClusterName': {'type': CFNString,
                        'description': 'The cluster name provided when the '
                                       'cluster was created. If it is '
                                       'incorrect, nodes will not be able to '
                                       'join the cluster.'},
        'BootstrapArguments': {'type': CFNString,
                               'description': 'Arguments to pass to the '
                                              'bootstrap script. See '
                                              'files/bootstrap.sh in '
                                              'https://github.com/awslabs/amazon-eks-ami',  # noqa
                               'default': ''},
        'NodeGroupName': {'type': CFNString,
                          'description': 'Unique identifier for the Node '
                                         'Group.'},
        'ClusterControlPlaneSecurityGroup': {'type': EC2SecurityGroupId,
                                             'description': 'The security '
                                                            'group of the '
                                                            'cluster control '
                                                            'plane.'},
        'VpcId': {'type': EC2VPCId,
                  'description': 'The VPC of the worker instances'},
        'Subnets': {'type': EC2SubnetIdList,
                    'description': 'The subnets where workers can be '
                                   'created.'},
        'UseDesiredInstanceCount': {'type': CFNString,
                                    'description': 'Should the initial '
                                                   'bootstrap instance count '
                                                   'be used?'},
        'UseSpotInstances': {'type': CFNString,
                             'default': 'no',
                             'allowed_values': ['yes', 'no'],
                             'description': 'Should the instances be '
                                            'configured as spot instances?'},
        'SpotBidPrice': {'type': CFNString,
                         'description': 'Bid price for Spot instance workers '
                                        '(only relevant if UseSpotInstances '
                                        'is set to "yes")',
                         'default': '0.68'},
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        variables = self.get_variables()
        template.add_version('2010-09-09')
        template.add_description('Kubernetes workers via EKS - V1.0.0 '
                                 '- compatible with amazon-eks-node-v23+')

        # Metadata
        template.add_metadata({
            'AWS::CloudFormation::Interface': {
                'ParameterGroups': [
                    {'Label': {'default': 'EKS Cluster'},
                     'Parameters': [variables[i].name
                                    for i
                                    in ['ClusterName',
                                        'ClusterControlPlaneSecurityGroup']]},
                    {'Label': {'default': 'Worker Node Configuration'},
                     'Parameters': [variables[i].name
                                    for i
                                    in ['NodeGroupName',
                                        'NodeAutoScalingGroupMinSize',
                                        'NodeAutoScalingGroupMaxSize',
                                        'UseDesiredInstanceCount',
                                        'NodeInstanceType',
                                        'NodeInstanceProfile',
                                        'NodeImageId',
                                        'NodeVolumeSize',
                                        'KeyName',
                                        'UseSpotInstances',
                                        'SpotBidPrice',
                                        'BootstrapArguments']]},
                    {'Label': {'default': 'Worker Network Configuration'},
                     'Parameters': [variables[i].name
                                    for i
                                    in ['VpcId', 'Subnets']]}
                ]
            }
        })

        # Conditions
        template.add_condition(
            'SetSpotPrice',
            Equals(variables['UseSpotInstances'].ref, 'yes')
        )
        template.add_condition(
            'DesiredInstanceCountSpecified',
            Equals(variables['UseDesiredInstanceCount'].ref, 'true')
        )
        template.add_condition(
            'KeyNameSpecified',
            Not(Equals(variables['KeyName'].ref, ''))
        )

        # Resources
        nodesecuritygroup = template.add_resource(
            ec2.SecurityGroup(
                'NodeSecurityGroup',
                GroupDescription='Security group for all nodes in the cluster',
                Tags=[
                    {'Key': Sub('kubernetes.io/cluster/${ClusterName}'),
                     'Value': 'owned'},
                ],
                VpcId=variables['VpcId'].ref
            )
        )
        template.add_output(
            Output(
                'NodeSecurityGroup',
                Description='Security group for all nodes in the cluster',
                Value=nodesecuritygroup.ref()
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                'NodeSecurityGroupIngress',
                Description='Allow node to communicate with each other',
                GroupId=nodesecuritygroup.ref(),
                SourceSecurityGroupId=nodesecuritygroup.ref(),
                IpProtocol='-1',
                FromPort=0,
                ToPort=65535
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                'NodeSecurityGroupFromControlPlaneIngress',
                Description='Allow worker Kubelets and pods to receive '
                            'communication from the cluster control plane',
                GroupId=nodesecuritygroup.ref(),
                SourceSecurityGroupId=variables['ClusterControlPlaneSecurityGroup'].ref,  # noqa
                IpProtocol='tcp',
                FromPort=1025,
                ToPort=65535
            )
        )
        template.add_resource(
            ec2.SecurityGroupEgress(
                'ControlPlaneEgressToNodeSecurityGroup',
                Description='Allow the cluster control plane to communicate '
                            'with worker Kubelet and pods',
                GroupId=variables['ClusterControlPlaneSecurityGroup'].ref,
                DestinationSecurityGroupId=nodesecuritygroup.ref(),
                IpProtocol='tcp',
                FromPort=1025,
                ToPort=65535
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                'NodeSecurityGroupFromControlPlaneOn443Ingress',
                Description='Allow pods running extension API servers on port '
                            '443 to receive communication from cluster '
                            'control plane',
                GroupId=nodesecuritygroup.ref(),
                SourceSecurityGroupId=variables['ClusterControlPlaneSecurityGroup'].ref,  # noqa
                IpProtocol='tcp',
                FromPort=443,
                ToPort=443
            )
        )
        template.add_resource(
            ec2.SecurityGroupEgress(
                'ControlPlaneEgressToNodeSecurityGroupOn443',
                Description='Allow the cluster control plane to communicate '
                            'with pods running extension API servers on port '
                            '443',
                GroupId=variables['ClusterControlPlaneSecurityGroup'].ref,
                DestinationSecurityGroupId=nodesecuritygroup.ref(),
                IpProtocol='tcp',
                FromPort=443,
                ToPort=443
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                'ClusterControlPlaneSecurityGroupIngress',
                Description='Allow pods to communicate with the cluster API '
                            'Server',
                GroupId=variables['ClusterControlPlaneSecurityGroup'].ref,
                SourceSecurityGroupId=nodesecuritygroup.ref(),
                IpProtocol='tcp',
                FromPort=443,
                ToPort=443
            )
        )

        nodelaunchconfig = template.add_resource(
            autoscaling.LaunchConfiguration(
                'NodeLaunchConfig',
                AssociatePublicIpAddress=True,
                IamInstanceProfile=variables['NodeInstanceProfile'].ref,
                ImageId=variables['NodeImageId'].ref,
                InstanceType=variables['NodeInstanceType'].ref,
                KeyName=If(
                    'KeyNameSpecified',
                    variables['KeyName'].ref,
                    NoValue
                ),
                SecurityGroups=[nodesecuritygroup.ref()],
                SpotPrice=If('SetSpotPrice',
                             variables['SpotBidPrice'].ref,
                             NoValue),
                BlockDeviceMappings=[autoscaling.BlockDeviceMapping(
                    DeviceName='/dev/xvda',
                    Ebs=autoscaling.EBSBlockDevice(
                        VolumeSize=variables['NodeVolumeSize'].ref,
                        VolumeType='gp2',
                        DeleteOnTermination=True
                    )
                )],
                UserData=Base64(
                    Sub('\n'.join([
                        '#!/bin/bash',
                        'set -o xtrace',
                        '/etc/eks/bootstrap.sh ${ClusterName} ${BootstrapArguments}',  # noqa
                        '/opt/aws/bin/cfn-signal --exit-code $? \\',
                        '--stack ${AWS::StackName} \\',
                        '--resource NodeGroup \\',
                        '--region ${AWS::Region}'
                    ]))
                )
            )
        )

        template.add_resource(
            autoscaling.AutoScalingGroup(
                'NodeGroup',
                DesiredCapacity=If(
                    'DesiredInstanceCountSpecified',
                    variables['NodeAutoScalingGroupMaxSize'].ref,
                    NoValue
                ),
                LaunchConfigurationName=nodelaunchconfig.ref(),
                MinSize=variables['NodeAutoScalingGroupMinSize'].ref,
                MaxSize=variables['NodeAutoScalingGroupMaxSize'].ref,
                VPCZoneIdentifier=variables['Subnets'].ref,
                Tags=[
                    autoscaling.Tag(
                        'Name',
                        Sub('${ClusterName}-${NodeGroupName}-Node'),
                        True),
                    autoscaling.Tag(
                        Sub('kubernetes.io/cluster/${ClusterName}'),
                        'owned',
                        True)
                ],
                UpdatePolicy=UpdatePolicy(
                    AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                        MinInstancesInService='1',
                        MaxBatchSize='1'
                    )
                )
            )
        )


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from runway.cfngin.context import Context
    print(NodeGroup('test', Context({"namespace": "test"}), None).to_json())
