#!/usr/bin/env python
"""Module with static website bucket and CloudFront distribution."""
from __future__ import print_function

import hashlib

from troposphere import (
    And, Equals, If, Join, Not, NoValue, Output, Select, awslambda, cloudfront,
    iam, s3
)

import awacs.s3
import awacs.sts
from awacs.aws import Allow, PolicyDocument, Principal, Statement

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNCommaDelimitedList, CFNString

IAM_ARN_PREFIX = 'arn:aws:iam::aws:policy/service-role/'


class StaticSite(Blueprint):  # pylint: disable=too-few-public-methods
    """Stacker blueprint for creating S3 bucket and CloudFront distribution."""

    VARIABLES = {
        'AcmCertificateArn': {'type': CFNString,
                              'default': '',
                              'description': '(Optional) Cert ARN for site'},
        'Aliases': {'type': CFNCommaDelimitedList,
                    'default': '',
                    'description': '(Optional) Domain aliases the '
                                   'distribution'},
        'LogBucketName': {'type': CFNString,
                          'default': '',
                          'description': 'S3 bucket for CF logs'},
        'PriceClass': {'type': CFNString,
                       'default': 'PriceClass_100',  # US/Europe
                       'description': 'CF price class for the distribution.'},
        'RewriteDirectoryIndex': {'type': CFNString,
                                  'default': '',
                                  'description': '(Optional) File name to '
                                                 'append to directory '
                                                 'requests.'},
        'WAFWebACL': {'type': CFNString,
                      'default': '',
                      'description': '(Optional) WAF id to associate with the '
                                     'distribution.'}
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        template = self.template
        variables = self.get_variables()
        template.add_version('2010-09-09')
        template.add_description('Static Website - Bucket and Distribution')

        # Conditions
        template.add_condition(
            'AcmCertSpecified',
            And(Not(Equals(variables['AcmCertificateArn'].ref, '')),
                Not(Equals(variables['AcmCertificateArn'].ref, 'undefined')))
        )
        template.add_condition(
            'AliasesSpecified',
            And(Not(Equals(Select(0, variables['Aliases'].ref), '')),
                Not(Equals(Select(0, variables['Aliases'].ref), 'undefined')))
        )
        template.add_condition(
            'CFLoggingEnabled',
            And(Not(Equals(variables['LogBucketName'].ref, '')),
                Not(Equals(variables['LogBucketName'].ref, 'undefined')))
        )
        template.add_condition(
            'DirectoryIndexSpecified',
            And(Not(Equals(variables['RewriteDirectoryIndex'].ref, '')),
                Not(Equals(variables['RewriteDirectoryIndex'].ref, 'undefined')))  # noqa
        )
        template.add_condition(
            'WAFNameSpecified',
            And(Not(Equals(variables['WAFWebACL'].ref, '')),
                Not(Equals(variables['WAFWebACL'].ref, 'undefined')))
        )

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
                PolicyDocument=PolicyDocument(
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

        cfdirectoryindexrewriterole = template.add_resource(
            iam.Role(
                'CFDirectoryIndexRewriteRole',
                Condition='DirectoryIndexSpecified',
                AssumeRolePolicyDocument=PolicyDocument(
                    Version='2012-10-17',
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Action=[awacs.sts.AssumeRole],
                            Principal=Principal('Service',
                                                ['lambda.amazonaws.com',
                                                 'edgelambda.amazonaws.com'])
                        )
                    ]
                ),
                ManagedPolicyArns=[
                    IAM_ARN_PREFIX + 'AWSLambdaBasicExecutionRole'
                ]
            )
        )

        cfdirectoryindexrewrite = template.add_resource(
            awslambda.Function(
                'CFDirectoryIndexRewrite',
                Condition='DirectoryIndexSpecified',
                Code=awslambda.Code(
                    ZipFile=Join(
                        '',
                        ["'use strict';\n",
                         "exports.handler = (event, context, callback) => {\n",
                         "\n",
                         "    // Extract the request from the CloudFront event that is sent to Lambda@Edge\n",  # noqa pylint: disable=line-too-long
                         "    var request = event.Records[0].cf.request;\n",
                         "    // Extract the URI from the request\n",
                         "    var olduri = request.uri;\n",
                         "    // Match any '/' that occurs at the end of a URI. Replace it with a default index\n",  # noqa pylint: disable=line-too-long
                         "    var newuri = olduri.replace(/\\/$/, '\\/",
                         variables['RewriteDirectoryIndex'].ref,
                         "');\n",  # noqa
                         "    // Log the URI as received by CloudFront and the new URI to be used to fetch from origin\n",  # noqa pylint: disable=line-too-long
                         "    console.log(\"Old URI: \" + olduri);\n",
                         "    console.log(\"New URI: \" + newuri);\n",
                         "    // Replace the received URI with the URI that includes the index page\n",  # noqa pylint: disable=line-too-long
                         "    request.uri = newuri;\n",
                         "    // Return to CloudFront\n",
                         "    return callback(null, request);\n",
                         "\n",
                         "};\n"]
                    )
                ),
                Description='Rewrites CF directory HTTP requests to default page',  # noqa
                Handler='index.handler',
                Role=cfdirectoryindexrewriterole.get_att('Arn'),
                Runtime='nodejs8.10'
            )
        )

        # Generating a unique resource name here for the Lambda version, so it
        # updates automatically if the lambda code changes
        code_hash = hashlib.md5(
            str(cfdirectoryindexrewrite.properties['Code'].properties['ZipFile'].to_dict()).encode()  # noqa pylint: disable=line-too-long
        ).hexdigest()

        cfdirectoryindexrewritever = template.add_resource(
            awslambda.Version(
                'CFDirectoryIndexRewriteVer' + code_hash,
                Condition='DirectoryIndexSpecified',
                FunctionName=cfdirectoryindexrewrite.ref()
            )
        )

        cfdistribution = template.add_resource(
            cloudfront.Distribution(
                'CFDistribution',
                DependsOn=allowcfaccess.title,
                DistributionConfig=cloudfront.DistributionConfig(
                    Aliases=If(
                        'AliasesSpecified',
                        variables['Aliases'].ref,
                        NoValue
                    ),
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
                        LambdaFunctionAssociations=If(
                            'DirectoryIndexSpecified',
                            [cloudfront.LambdaFunctionAssociation(
                                EventType='origin-request',
                                LambdaFunctionARN=cfdirectoryindexrewritever.ref()  # noqa
                            )],
                            NoValue
                        ),
                        TargetOriginId='S3Origin',
                        ViewerProtocolPolicy='redirect-to-https'
                    ),
                    DefaultRootObject='index.html',
                    Logging=If(
                        'CFLoggingEnabled',
                        cloudfront.Logging(
                            Bucket=Join('.',
                                        [variables['LogBucketName'].ref,
                                         's3.amazonaws.com'])
                        ),
                        NoValue
                    ),
                    PriceClass=variables['PriceClass'].ref,
                    Enabled=True,
                    WebACLId=If(
                        'WAFNameSpecified',
                        variables['WAFWebACL'].ref,
                        NoValue
                    ),
                    ViewerCertificate=If(
                        'AcmCertSpecified',
                        cloudfront.ViewerCertificate(
                            AcmCertificateArn=variables['AcmCertificateArn'].ref,  # noqa
                            SslSupportMethod='sni-only'
                        ),
                        NoValue
                    )
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
