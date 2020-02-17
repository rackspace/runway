#!/usr/bin/env python
"""Module with static website bucket and CloudFront distribution."""
from __future__ import print_function

import hashlib
# https://github.com/PyCQA/pylint/issues/73
from distutils.version import LooseVersion  # noqa pylint: disable=no-name-in-module,import-error
from past.builtins import basestring

import awacs.s3
import awacs.sts
from awacs.aws import Action, Allow, Policy, PolicyDocument, Principal, Statement

import troposphere
from troposphere import (
    AWSProperty, And, Equals, If, Join, Not, NoValue, Output, Select,
    awslambda, cloudfront, iam, s3
)

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.blueprints.variables.types import CFNCommaDelimitedList, CFNString
from runway.cfngin.context import Context

IAM_ARN_PREFIX = 'arn:aws:iam::aws:policy/service-role/'
if LooseVersion(troposphere.__version__) == LooseVersion('2.4.0'):
    # pylint: disable=ungrouped-imports
    from troposphere.validators import boolean, priceclass_type

    class S3OriginConfig(AWSProperty):
        """Backported s3 origin config class for broken troposphere release."""

        props = {
            'OriginAccessIdentity': (basestring, False),
        }

    class Origin(AWSProperty):
        """Backported origin config class for broken troposphere release."""

        props = {
            'CustomOriginConfig': (cloudfront.CustomOriginConfig, False),
            'DomainName': (basestring, True),
            'Id': (basestring, True),
            'OriginCustomHeaders': ([cloudfront.OriginCustomHeader], False),
            'OriginPath': (basestring, False),
            'S3OriginConfig': (S3OriginConfig, False),
        }

    class DistributionConfig(AWSProperty):
        """Backported cf config class for broken troposphere release."""

        props = {
            'Aliases': (list, False),
            'CacheBehaviors': ([cloudfront.CacheBehavior], False),
            'Comment': (basestring, False),
            'CustomErrorResponses': ([cloudfront.CustomErrorResponse], False),
            'DefaultCacheBehavior': (cloudfront.DefaultCacheBehavior, True),
            'DefaultRootObject': (basestring, False),
            'Enabled': (boolean, True),
            'HttpVersion': (basestring, False),
            'IPV6Enabled': (boolean, False),
            'Logging': (cloudfront.Logging, False),
            'Origins': ([Origin], True),
            'PriceClass': (priceclass_type, False),
            'Restrictions': (cloudfront.Restrictions, False),
            'ViewerCertificate': (cloudfront.ViewerCertificate, False),
            'WebACLId': (basestring, False),
        }


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
        'DisableCloudFront': {'type': CFNString,
                              'default': '',
                              'description': 'Whether to disable CF'},
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
                                     'distribution.'},
        'custom_error_responses': {'type': list,
                                   'default': [],
                                   'description': '(Optional) Custom error '
                                                  'responses.'},
        'lambda_function_associations': {'type': list,
                                         'default': [],
                                         'description': '(Optional) Lambda '
                                                        'function '
                                                        'associations.'},
    }

    def create_template(self):
        """Create template (main function called by Stacker)."""
        self.template.set_version('2010-09-09')
        self.template.set_description('Static Website - Bucket and Distribution')

        self.add_template_conditions()

        # Resources
        bucket = self.add_bucket()
        bucket_policy = self.add_bucket_policy(bucket) # noqa pylint: disable=unused-variable
        oai = self.add_origin_access_identity()
        allow_access = self.allow_cloudfront_access_on_bucket(bucket, oai)
        rewrite_role = self.add_index_rewrite_role()
        index_rewrite = self.add_cloudfront_directory_index_rewrite(rewrite_role)
        index_rewrite_version = self.add_cloudfront_directory_index_rewrite_version(
            index_rewrite
        )
        lambda_function_associations = self.get_lambda_associations(index_rewrite_version)
        distribution_options = self.get_cloudfront_distribution_options(
            bucket,
            oai,
            lambda_function_associations
        )
        distribution = self.add_cloudfront_distribution( # noqa pylint: disable=unused-variable
            allow_access,
            distribution_options
        )

    def add_template_conditions(self):
        """Add Template Conditions."""
        variables = self.get_variables()

        self.template.add_condition(
            'AcmCertSpecified',
            And(Not(Equals(variables['AcmCertificateArn'].ref, '')),
                Not(Equals(variables['AcmCertificateArn'].ref, 'undefined')))
        )
        self.template.add_condition(
            'AliasesSpecified',
            And(Not(Equals(Select(0, variables['Aliases'].ref), '')),
                Not(Equals(Select(0, variables['Aliases'].ref), 'undefined')))
        )
        self.template.add_condition(
            'CFEnabled',
            Not(Equals(variables['DisableCloudFront'].ref, 'true'))
        )
        self.template.add_condition(
            'CFDisabled',
            Equals(variables['DisableCloudFront'].ref, 'true')
        )
        self.template.add_condition(
            'CFLoggingEnabled',
            And(Not(Equals(variables['LogBucketName'].ref, '')),
                Not(Equals(variables['LogBucketName'].ref, 'undefined')))
        )
        self.template.add_condition(
            'DirectoryIndexSpecified',
            And(Not(Equals(variables['RewriteDirectoryIndex'].ref, '')),
                Not(Equals(variables['RewriteDirectoryIndex'].ref, 'undefined')))  # noqa
        )
        self.template.add_condition(
            'CFEnabledAndDirectoryIndexSpecified',
            And(Not(Equals(variables['RewriteDirectoryIndex'].ref, '')),
                Not(Equals(variables['RewriteDirectoryIndex'].ref, 'undefined')), # noqa
                Not(Equals(variables['DisableCloudFront'].ref, 'true')))
        )
        self.template.add_condition(
            'WAFNameSpecified',
            And(Not(Equals(variables['WAFWebACL'].ref, '')),
                Not(Equals(variables['WAFWebACL'].ref, 'undefined')))
        )

    def get_lambda_associations(self, directory_index_rewrite_version):
        """Retrieve any lambda associations from the instance variables.

        Keyword Args:
            directory_index_rewrite_version (dict): The directory index rewrite lambda version
                resource

        Return:
            array: Array of lambda function association variables
        """
        variables = self.get_variables()

        # If custom associations defined, use them
        if variables['lambda_function_associations']:
            return [
                cloudfront.LambdaFunctionAssociation(
                    EventType=x['type'],
                    LambdaFunctionARN=x['arn']
                ) for x in variables['lambda_function_associations']
            ]

        # otherwise fallback to pure CFN condition
        return If(
            'DirectoryIndexSpecified',
            [cloudfront.LambdaFunctionAssociation(
                EventType='origin-request',
                LambdaFunctionARN=directory_index_rewrite_version.ref()
            )],
            NoValue
        )

    def get_cloudfront_distribution_options(self, bucket, oai, lambda_function_associations):
        """Retrieve the options for our CloudFront distribution.

        Keyword Args:
            bucket (dict): The bucket resource
            oai (dict): The origin access identity resource
            lambda_function_associations (array): The lambda function association array

        Return:
            dict: The CloudFront Distribution Options

        """
        variables = self.get_variables()
        return {
            'Aliases': If(
                'AliasesSpecified',
                variables['Aliases'].ref,
                NoValue
            ),
            'Origins': [
                get_cf_origin_class()(
                    DomainName=Join(
                        '.',
                        [bucket.ref(),
                         's3.amazonaws.com']),
                    S3OriginConfig=get_s3_origin_conf_class()(
                        OriginAccessIdentity=Join(
                            '',
                            ['origin-access-identity/cloudfront/',
                             oai.ref()])
                    ),
                    Id='S3Origin'
                )
            ],
            'DefaultCacheBehavior': cloudfront.DefaultCacheBehavior(
                AllowedMethods=['GET', 'HEAD'],
                Compress=False,
                DefaultTTL='86400',
                ForwardedValues=cloudfront.ForwardedValues(
                    Cookies=cloudfront.Cookies(Forward='none'),
                    QueryString=False,
                ),
                LambdaFunctionAssociations=lambda_function_associations,
                TargetOriginId='S3Origin',
                ViewerProtocolPolicy='redirect-to-https'
            ),
            'DefaultRootObject': 'index.html',
            'Logging': If(
                'CFLoggingEnabled',
                cloudfront.Logging(
                    Bucket=Join('.',
                                [variables['LogBucketName'].ref,
                                 's3.amazonaws.com'])
                ),
                NoValue
            ),
            'PriceClass': variables['PriceClass'].ref,
            'Enabled': True,
            'WebACLId': If(
                'WAFNameSpecified',
                variables['WAFWebACL'].ref,
                NoValue
            ),
            'ViewerCertificate': If(
                'AcmCertSpecified',
                cloudfront.ViewerCertificate(
                    AcmCertificateArn=variables['AcmCertificateArn'].ref,
                    SslSupportMethod='sni-only'
                ),
                NoValue
            )
        }

    def add_origin_access_identity(self):
        """Add the origin access identity resource to the template.

        Returns:
            dict: The OAI resource

        """
        return self.template.add_resource(
            cloudfront.CloudFrontOriginAccessIdentity(
                'OAI',
                Condition='CFEnabled',
                CloudFrontOriginAccessIdentityConfig=cloudfront.CloudFrontOriginAccessIdentityConfig(  # noqa pylint: disable=line-too-long
                    Comment='CF access to website'
                )
            )
        )

    def add_bucket_policy(self, bucket):
        """Add a policy to the bucket if CloudFront is disabled. Ensure PublicRead.

        Keyword Args:
            bucket (dict): The bucket resource to place the policy

        Returns:
            dict: The Bucket Policy Resource

        """
        return self.template.add_resource(
            s3.BucketPolicy(
                'BucketPolicy',
                Bucket=bucket.ref(),
                Condition='CFDisabled',
                PolicyDocument=Policy(
                    Version="2012-10-17",
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Principal=Principal('*'),
                            Action=[Action('s3', 'getObject')],
                            Resource=[
                                Join('', [bucket.get_att('Arn'), '/*'])
                            ],
                        )
                    ]
                )
            )
        )

    def add_bucket(self):
        """Add the bucket resource along with an output of it's name / website url.

        Returns:
            dict: The bucket resource

        """
        bucket = self.template.add_resource(
            s3.Bucket(
                'Bucket',
                AccessControl=If('CFEnabled', s3.Private, s3.PublicRead),
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
        self.template.add_output(Output(
            'BucketName',
            Description='Name of website bucket',
            Value=bucket.ref()
        ))
        self.template.add_output(Output(
            'BucketWebsiteURL',
            Condition="CFDisabled",
            Description='URL of the bucket website',
            Value=bucket.get_att('WebsiteURL')
        ))
        return bucket

    def allow_cloudfront_access_on_bucket(self, bucket, oai):
        """Given a bucket and oai resource add cloudfront access to the bucket.

        Keyword Args:
            bucket (dict): A bucket resource
            oai (dict): An Origin Access Identity resource

        Return:
            dict: The CloudFront Bucket access resource
        """
        return self.template.add_resource(
            s3.BucketPolicy(
                'AllowCFAccess',
                Bucket=bucket.ref(),
                Condition='CFEnabled',
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

    def add_index_rewrite_role(self):
        """Add an index rewrite role to the template.

        Return:
            dict: The index rewrite role
        """
        return self.template.add_resource(
            iam.Role(
                'CFDirectoryIndexRewriteRole',
                Condition='CFEnabledAndDirectoryIndexSpecified',
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

    def add_cloudfront_directory_index_rewrite(self, role):
        """Add an index CloudFront directory index rewrite lambda function to the template.

        Keyword Args:
            role (dict): The index rewrite role resource

        Return:
            dict: The CloudFront directory index rewrite lambda function resource
        """
        variables = self.get_variables()
        return self.template.add_resource(
            awslambda.Function(
                'CFDirectoryIndexRewrite',
                Condition='CFEnabledAndDirectoryIndexSpecified',
                Code=awslambda.Code(
                    ZipFile=Join(
                        '',
                        ["'use strict';\n",
                         "exports.handler = async function(event, context) {\n",
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
                         "    return request;\n",
                         "\n",
                         "};\n"]
                    )
                ),
                Description='Rewrites CF directory HTTP requests to default page',  # noqa
                Handler='index.handler',
                Role=role.get_att('Arn'),
                Runtime='nodejs10.x'
            )
        )

    def add_cloudfront_directory_index_rewrite_version(self, directory_index_rewrite):
        """Add a specific version to the directory index rewrite lambda.

        Keyword Args:
            directory_index_rewrite (dict): The directory index rewrite lambda resource

        Return:
            dict: The CloudFront directory index rewrite version

        """
        # Generating a unique resource name here for the Lambda version, so it
        # updates automatically if the lambda code changes
        code_hash = hashlib.md5(
            str(directory_index_rewrite.properties['Code'].properties['ZipFile'].to_dict()).encode()  # noqa pylint: disable=line-too-long
        ).hexdigest()

        return self.template.add_resource(
            awslambda.Version(
                'CFDirectoryIndexRewriteVer' + code_hash,
                Condition='CFEnabledAndDirectoryIndexSpecified',
                FunctionName=directory_index_rewrite.ref()
            )
        )

    def add_cloudfront_distribution(
            self,
            allow_cloudfront_access,
            cloudfront_distribution_options
    ):
        """Add the CloudFront distribution to the template / output the id and domain name.

        Keyword Args:
            allow_cloudfront_access (dict): Allow bucket access resource
            cloudfront_distribution_options (dict): The distribution options

        Return:
            dict: The CloudFront Distribution resource

        """
        distribution = self.template.add_resource(
            get_cf_distribution_class()(
                'CFDistribution',
                Condition='CFEnabled',
                DependsOn=allow_cloudfront_access.title,
                DistributionConfig=get_cf_distro_conf_class()(
                    **cloudfront_distribution_options
                )
            )
        )
        self.template.add_output(Output(
            'CFDistributionId',
            Condition='CFEnabled',
            Description='CloudFront distribution ID',
            Value=distribution.ref()
        ))
        self.template.add_output(
            Output(
                'CFDistributionDomainName',
                Condition='CFEnabled',
                Description='CloudFront distribution domain name',
                Value=distribution.get_att('DomainName')
            )
        )
        return distribution


def get_cf_distribution_class():
    """Return the correct troposphere CF distribution class."""
    if LooseVersion(troposphere.__version__) == LooseVersion('2.4.0'):
        cf_dist = cloudfront.Distribution
        cf_dist.props['DistributionConfig'] = (DistributionConfig, True)
        return cf_dist
    return cloudfront.Distribution


def get_cf_distro_conf_class():
    """Return the correct troposphere CF distribution class."""
    if LooseVersion(troposphere.__version__) == LooseVersion('2.4.0'):
        return DistributionConfig
    return cloudfront.DistributionConfig


def get_cf_origin_class():
    """Return the correct Origin class for troposphere."""
    if LooseVersion(troposphere.__version__) == LooseVersion('2.4.0'):
        return Origin
    return cloudfront.Origin


def get_s3_origin_conf_class():
    """Return the correct S3 Origin Config class for troposphere."""
    if LooseVersion(troposphere.__version__) > LooseVersion('2.4.0'):
        return cloudfront.S3OriginConfig
    if LooseVersion(troposphere.__version__) == LooseVersion('2.4.0'):
        return S3OriginConfig
    return cloudfront.S3Origin


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    print(StaticSite('test', Context({"namespace": "test"}), None).to_json())
