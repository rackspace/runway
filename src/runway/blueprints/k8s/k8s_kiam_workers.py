#!/usr/bin/env python
"""Module with k8s nodegroup."""
from __future__ import print_function

import json
import os
import sys

from troposphere import (
    Base64, Equals, If, NoValue, Select, Sub, autoscaling, ec2
)
from troposphere.policies import AutoScalingRollingUpdate, UpdatePolicy

import botocore

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import (
    CFNNumber, CFNString, EC2ImageId, EC2KeyPairKeyName, EC2SecurityGroupId,
    EC2SubnetIdList, EC2VPCId
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
        'KeyName': {'type': EC2KeyPairKeyName,
                    'description': 'The EC2 Key Pair to allow SSH access to '
                                   'the instances'},
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
        'WorkerNodeSecurityGroup': {'type': EC2SecurityGroupId,
                                    'description': 'The security group of the '
                                                   'worker nodes.'},
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
        template.add_description('Kubernetes KIAM workers via EKS - V1.0.0 '
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
                                    in ['WorkerNodeSecurityGroup']]},
                    {'Label': {'default': 'Kiam Worker Node Configuration'},
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
                    {'Label': {'default': 'Kiam Worker Network Configuration'},
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

        # Resources
        kiamnodesecuritygroup = template.add_resource(
            ec2.SecurityGroup(
                'KiamNodeSecurityGroup',
                GroupDescription='Security group for kiam nodes in the cluster',
                Tags=[
                    {'Key': Sub('kubernetes.io/cluster/${ClusterName}'),
                     'Value': 'owned'},
                ],
                VpcId=variables['VpcId'].ref
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                'KiamNodeSecurityGroupIngress',
                Description='Allow node to communicate with each other',
                GroupId=kiamnodesecuritygroup.ref(),
                SourceSecurityGroupId=kiamnodesecuritygroup.ref(),
                IpProtocol='-1',
                FromPort=0,
                ToPort=65535
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                'KiamNodeSecurityGroupFromControlPlaneIngress',
                Description='Allow worker Kubelets and pods to receive '
                            'communication from the cluster control plane',
                GroupId=kiamnodesecuritygroup.ref(),
                SourceSecurityGroupId=variables['ClusterControlPlaneSecurityGroup'].ref,  # noqa
                IpProtocol='tcp',
                FromPort=1025,
                ToPort=65535
            )
        )
        template.add_resource(
            ec2.SecurityGroupEgress(
                'ControlPlaneEgressToKiamNodeSecurityGroup',
                Description='Allow the cluster control plane to communicate '
                            'with worker Kubelet and pods',
                GroupId=variables['ClusterControlPlaneSecurityGroup'].ref,
                DestinationSecurityGroupId=kiamnodesecuritygroup.ref(),
                IpProtocol='tcp',
                FromPort=1025,
                ToPort=65535
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                'KiamNodeSecurityGroupFromControlPlaneOn443Ingress',
                Description='Allow pods running extension API servers on port '
                            '443 to receive communication from cluster '
                            'control plane',
                GroupId=kiamnodesecuritygroup.ref(),
                SourceSecurityGroupId=variables['ClusterControlPlaneSecurityGroup'].ref,  # noqa
                IpProtocol='tcp',
                FromPort=443,
                ToPort=443
            )
        )
        template.add_resource(
            ec2.SecurityGroupEgress(
                'ControlPlaneEgressToKiamNodeSecurityGroupOn443',
                Description='Allow the cluster control plane to communicate '
                            'with pods running extension API servers on port '
                            '443',
                GroupId=variables['ClusterControlPlaneSecurityGroup'].ref,
                DestinationSecurityGroupId=kiamnodesecuritygroup.ref(),
                IpProtocol='tcp',
                FromPort=443,
                ToPort=443
            )
        )
        template.add_resource(
            ec2.SecurityGroupIngress(
                'ClusterControlPlaneKiamSecurityGroupIngress',
                Description='Allow pods to communicate with the cluster API '
                            'Server',
                GroupId=variables['ClusterControlPlaneSecurityGroup'].ref,
                SourceSecurityGroupId=kiamnodesecuritygroup.ref(),
                IpProtocol='tcp',
                FromPort=443,
                ToPort=443
            )
        )

        template.add_resource(
            ec2.SecurityGroupIngress(
                'KiamFromWorkerSecurityGroupIngress',
                Description='Allow kiam nodes to receive requests from worker '
                            'nodes',
                GroupId=kiamnodesecuritygroup.ref(),
                SourceSecurityGroupId=variables['WorkerNodeSecurityGroup'].ref,
                IpProtocol='-1',
                FromPort=0,
                ToPort=65535
            )
        )

        template.add_resource(
            ec2.SecurityGroupIngress(
                'WorkerDNSFromKiamSecurityGroupIngress',
                Description='Allow kiam nodes to send DNS requests to '
                            'kube-dns on worker nodes',
                GroupId=variables['WorkerNodeSecurityGroup'].ref,
                SourceSecurityGroupId=kiamnodesecuritygroup.ref(),
                IpProtocol='udp',
                FromPort=53,
                ToPort=53
            )
        )

        nodelaunchconfig = template.add_resource(
            autoscaling.LaunchConfiguration(
                'NodeLaunchConfig',
                AssociatePublicIpAddress=True,
                IamInstanceProfile=variables['NodeInstanceProfile'].ref,
                ImageId=variables['NodeImageId'].ref,
                InstanceType=variables['NodeInstanceType'].ref,
                KeyName=variables['KeyName'].ref,
                SecurityGroups=[kiamnodesecuritygroup.ref()],
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

        # Hardcoded to 3 subnets for now because:
        # 1) kiam will soon be replaced:
        #    https://github.com/aws/containers-roadmap/issues/23
        # 2) This template will be used after conversion to raw CFN yaml, so
        #    we can't rely on template-generation-time python logic
        for i in range(3):
            template.add_resource(
                autoscaling.AutoScalingGroup(
                    'NodeGroup' + str(i + 1),
                    DesiredCapacity=If(
                        'DesiredInstanceCountSpecified',
                        variables['NodeAutoScalingGroupMinSize'].ref,
                        NoValue
                    ),
                    LaunchConfigurationName=nodelaunchconfig.ref(),
                    MinSize=variables['NodeAutoScalingGroupMinSize'].ref,
                    MaxSize=variables['NodeAutoScalingGroupMaxSize'].ref,
                    VPCZoneIdentifier=[Select(
                        i,
                        variables['Subnets'].ref
                    )],
                    Tags=[
                        autoscaling.Tag(
                            'Name',
                            Sub("${ClusterName}-${NodeGroupName}-%s-Node" % str(i +1)),  # noqa
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
    from stacker.context import Context
    print(NodeGroup('test', Context({"namespace": "test"}), None).to_json())
