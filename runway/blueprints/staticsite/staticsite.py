#!/usr/bin/env python
"""Module with static website bucket and CloudFront distribution."""
from __future__ import print_function

from troposphere import Join, Output, cloudfront, s3

import awacs.s3
from awacs.aws import Allow, Policy, Principal, Statement

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNString


class StaticSite(Blueprint):
    """Stacker blueprint for creating S3 bucket and CloudFront distribution."""

    VARIABLES = {
        'LogBucketName': {'type': CFNString,
                          'default': '',
                          'description': 'S3 bucket for CF logs'}
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        variables = self.get_variables()
        template.add_version('2010-09-09')
        template.add_description('Static Website - Bucket and Distribution')

        # Resources
        oai = template.add_resource(
            cloudfront.CloudFrontOriginAccessIdentity(
                'OAI',
                CloudFrontOriginAccessIdentityConfig=cloudfront.CloudFrontOriginAccessIdentityConfig(  # noqa pylint: disable=line-too-long
                    Comment='CF access to website'
                )
            )
        )

        bucket = template.add_resource(
            s3.Bucket(
                'Bucket',
                AccessControl=s3.Private,
                LifecycleConfiguration=s3.LifecycleConfiguration(
                    Rules=[
                        s3.LifecycleRule(
                            NoncurrentVersionExpirationInDays=90,
                            Status='Enabled'
                        )
                    ]
                ),
                VersioningConfiguration=s3.VersioningConfiguration(
                    Status='Enabled'
                ),
                WebsiteConfiguration=s3.WebsiteConfiguration(
                    IndexDocument='index.html',
                    ErrorDocument='error.html'
                )
            )
        )
        template.add_output(Output(
            'BucketName',
            Description='Name of website bucket',
            Value=bucket.ref()
        ))

        allowcfaccess = template.add_resource(
            s3.BucketPolicy(
                'AllowCFAccess',
                Bucket=bucket.ref(),
                PolicyDocument=Policy(
                    Version='2012-10-17',
                    Statement=[
                        Statement(
                            Action=[awacs.s3.GetObject],
                            Effect=Allow,
                            Principal=Principal(
                                'CanonicalUser',
                                oai.get_att('S3CanonicalUserId')
                            ),
                            Resource=[
                                Join('', [bucket.get_att('Arn'),
                                          '/*'])
                            ]
                        )
                    ]
                )
            )
        )

        cfdistribution = template.add_resource(
            cloudfront.Distribution(
                'CFDistribution',
                DependsOn=allowcfaccess.title,
                DistributionConfig=cloudfront.DistributionConfig(
                    Origins=[
                        cloudfront.Origin(
                            DomainName=Join(
                                '.',
                                [bucket.ref(),
                                 's3.amazonaws.com']),
                            S3OriginConfig=cloudfront.S3Origin(
                                OriginAccessIdentity=Join(
                                    '',
                                    ['origin-access-identity/cloudfront/',
                                     oai.ref()])
                            ),
                            Id='S3Origin'
                        )
                    ],
                    DefaultCacheBehavior=cloudfront.DefaultCacheBehavior(
                        AllowedMethods=['GET', 'HEAD'],
                        Compress=False,
                        DefaultTTL='86400',
                        ForwardedValues=cloudfront.ForwardedValues(
                            Cookies=cloudfront.Cookies(Forward='none'),
                            QueryString=False,
                        ),
                        TargetOriginId='S3Origin',
                        ViewerProtocolPolicy='redirect-to-https'
                    ),
                    DefaultRootObject='index.html',
                    # Aliases=['example.com'],
                    Logging=cloudfront.Logging(
                        Bucket=Join('.',
                                    [variables['LogBucketName'].ref,
                                     's3.amazonaws.com'])
                    ),
                    PriceClass='PriceClass_100',
                    Enabled=True,
                    # ViewerCertificate=cloudfront.ViewerCertificate(
                    #     AcmCertificateArn=variables['AcmCertificateArn'].ref,
                    #     SslSupportMethod='sni-only'
                    # )
                )
            )
        )
        template.add_output(Output(
            'CFDistributionId',
            Description='CloudFront distribution ID',
            Value=cfdistribution.ref()
        ))
        template.add_output(
            Output(
                'CFDistributionDomainName',
                Description='CloudFront distribution domain name',
                Value=cfdistribution.get_att('DomainName')
            )
        )


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    from stacker.context import Context
    print(StaticSite('test', Context({"namespace": "test"}), None).to_json())
