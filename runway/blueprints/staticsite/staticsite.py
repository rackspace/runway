#!/usr/bin/env python
"""Module with static website bucket and CloudFront distribution."""
from __future__ import print_function

import hashlib
import logging
import os
from typing import Any, Dict, List, Union  # pylint: disable=unused-import

import awacs.awslambda
import awacs.iam
import awacs.logs
import awacs.s3
import awacs.states
import awacs.sts
from awacs.aws import Action, Allow, Policy, PolicyDocument, Principal, Statement
from awacs.helpers.trust import make_simple_assume_policy
from troposphere import (  # noqa pylint: disable=unused-import
    AccountId,
    Join,
    NoValue,
    Output,
    Partition,
    Region,
    StackName,
    Sub,
    awslambda,
    cloudfront,
    iam,
    logs,
    s3,
    stepfunctions,
)

from runway.cfngin.blueprints.base import Blueprint
from runway.cfngin.context import Context

LOGGER = logging.getLogger("runway")

IAM_ARN_PREFIX = "arn:aws:iam::aws:policy/service-role/"


class StaticSite(Blueprint):  # pylint: disable=too-few-public-methods
    """CFNgin blueprint for creating S3 bucket and CloudFront distribution."""

    VARIABLES = {
        "AcmCertificateArn": {
            "type": str,
            "default": "",
            "description": "(Optional) Cert ARN for site",
        },
        "Aliases": {
            "type": list,
            "default": [],
            "description": "(Optional) Domain aliases the " "distribution",
        },
        "DisableCloudFront": {
            "type": bool,
            "default": False,
            "description": "Whether to disable CF",
        },
        "LogBucketName": {
            "type": str,
            "default": "",
            "description": "S3 bucket for CF logs",
        },
        "PriceClass": {
            "type": str,
            "default": "PriceClass_100",  # US/Europe
            "description": "CF price class for the distribution.",
        },
        "RewriteDirectoryIndex": {
            "type": str,
            "default": "",
            "description": "(Optional) File name to "
            "append to directory "
            "requests.",
        },
        "RoleBoundaryArn": {
            "type": str,
            "default": "",
            "description": "(Optional) IAM Role permissions "
            "boundary applied to any created "
            "roles.",
        },
        "WAFWebACL": {
            "type": str,
            "default": "",
            "description": "(Optional) WAF id to associate with the " "distribution.",
        },
        "custom_error_responses": {
            "type": list,
            "default": [],
            "description": "(Optional) Custom error " "responses.",
        },
        "lambda_function_associations": {
            "type": list,
            "default": [],
            "description": "(Optional) Lambda " "function " "associations.",
        },
    }

    @property
    def aliases_specified(self):
        # type: () -> bool
        """Aliases are specified conditional."""
        return self.get_variables()["Aliases"] != [""]

    @property
    def cf_enabled(self):
        # type: () -> bool
        """CloudFront enabled conditional."""
        return not self.get_variables().get("DisableCloudFront", False)

    @property
    def acm_certificate_specified(self):
        # type: () -> bool
        """ACM Certification specified conditional."""
        return self.get_variables()["AcmCertificateArn"] != ""

    @property
    def cf_logging_enabled(self):
        # type: () -> bool
        """CloudFront Logging specified conditional."""
        return self.get_variables()["LogBucketName"] != ""

    @property
    def directory_index_specified(self):
        # type: () -> bool
        """Directory Index specified conditional."""
        return self.get_variables()["RewriteDirectoryIndex"] != ""

    @property
    def role_boundary_specified(self):
        # type: () -> bool
        """IAM Role Boundary specified conditional."""
        return self.get_variables()["RoleBoundaryArn"] != ""

    @property
    def waf_name_specified(self):
        # type: () -> bool
        """WAF name specified conditional."""
        return self.get_variables()["WAFWebACL"] != ""

    def create_template(self):
        # type: () -> None
        """Create template (main function called by CFNgin)."""
        self.template.set_version("2010-09-09")
        self.template.set_description("Static Website - Bucket and Distribution")

        # Resources
        bucket = self.add_bucket()

        if self.cf_enabled:
            oai = self.add_origin_access_identity()
            bucket_policy = self.add_cloudfront_bucket_policy(bucket, oai)
            lambda_function_associations = self.get_lambda_associations()

            if self.directory_index_specified:
                index_rewrite = self._get_index_rewrite_role_function_and_version()
                lambda_function_associations = self.get_directory_index_lambda_association(
                    lambda_function_associations, index_rewrite["version"]
                )

            distribution_options = self.get_cloudfront_distribution_options(
                bucket, oai, lambda_function_associations
            )
            distribution = self.add_cloudfront_distribution(  # noqa pylint: disable=unused-variable
                bucket_policy, distribution_options
            )
        else:
            self.add_bucket_policy(bucket)

    def get_lambda_associations(self):
        # type: () -> List[cloudfront.LambdaFunctionAssociation]
        """Retrieve any lambda associations from the instance variables.

        Return:
            List of Lambda Function association variables

        """
        variables = self.get_variables()

        # If custom associations defined, use them
        if variables["lambda_function_associations"]:
            return [
                cloudfront.LambdaFunctionAssociation(
                    EventType=x["type"], LambdaFunctionARN=x["arn"]
                )
                for x in variables["lambda_function_associations"]
            ]
        return []

    def get_directory_index_lambda_association(  # pylint: disable=no-self-use
        self,
        lambda_associations,  # type: List[cloudfront.LambdaFunctionAssociation]
        directory_index_rewrite_version,  # type: awslambda.Version
    ):
        # type: (...) ->  List[cloudfront.LambdaFunctionAssociation]
        """Retrieve the directory index lambda associations with the added rewriter.

        Args:
            lambda_associations: The lambda associations.
            directory_index_rewrite_version: The directory index rewrite version.

        """
        lambda_associations.append(
            cloudfront.LambdaFunctionAssociation(
                EventType="origin-request",
                LambdaFunctionARN=directory_index_rewrite_version.ref(),
            )
        )
        return lambda_associations

    def get_cloudfront_distribution_options(
        self,
        bucket,  # type: s3.Bucket
        oai,  # type: cloudfront.CloudFrontOriginAccessIdentity
        lambda_function_associations,  # type: List[cloudfront.LambdaFunctionAssociation]
    ):
        # type: (...) -> Dict[str, Any]
        """Retrieve the options for our CloudFront distribution.

        Args:
            bucket: The bucket resource
            oai: The origin access identity resource.
            lambda_function_associations: List of Lambda Function associations.

        Return:
            The CloudFront Distribution Options.

        """
        variables = self.get_variables()
        return {
            "Aliases": self.add_aliases(),
            "Origins": [
                cloudfront.Origin(
                    DomainName=Join(".", [bucket.ref(), "s3.amazonaws.com"]),
                    S3OriginConfig=cloudfront.S3OriginConfig(
                        OriginAccessIdentity=Join(
                            "", ["origin-access-identity/cloudfront/", oai.ref()]
                        )
                    ),
                    Id="S3Origin",
                )
            ],
            "DefaultCacheBehavior": cloudfront.DefaultCacheBehavior(
                AllowedMethods=["GET", "HEAD"],
                Compress=False,
                DefaultTTL="86400",
                ForwardedValues=cloudfront.ForwardedValues(
                    Cookies=cloudfront.Cookies(Forward="none"), QueryString=False,
                ),
                LambdaFunctionAssociations=lambda_function_associations,
                TargetOriginId="S3Origin",
                ViewerProtocolPolicy="redirect-to-https",
            ),
            "DefaultRootObject": "index.html",
            "Logging": self.add_logging_bucket(),
            "PriceClass": variables["PriceClass"],
            "CustomErrorResponses": [
                cloudfront.CustomErrorResponse(
                    ErrorCode=response["ErrorCode"],
                    ResponseCode=response["ResponseCode"],
                    ResponsePagePath=response["ResponsePagePath"],
                )
                for response in variables["custom_error_responses"]
            ],
            "Enabled": True,
            "WebACLId": self.add_web_acl(),
            "ViewerCertificate": self.add_acm_cert(),
        }

    def add_aliases(self):
        # type: () -> Union[List[str], NoValue]
        """Add aliases."""
        if self.aliases_specified:
            return self.get_variables()["Aliases"]
        return NoValue

    def add_web_acl(self):
        # type: () -> Union[str, NoValue]
        """Add Web ACL."""
        if self.waf_name_specified:
            return self.get_variables()["WAFWebACL"]
        return NoValue

    def add_logging_bucket(self):
        # type: () -> Union[cloudfront.Logging, NoValue]
        """Add Logging Bucket."""
        if self.cf_logging_enabled:
            return cloudfront.Logging(
                Bucket=Join(
                    ".", [self.get_variables()["LogBucketName"], "s3.amazonaws.com"]
                )
            )
        return NoValue

    def add_acm_cert(self):
        # type: () -> Union[cloudfront.ViewerCertificate, NoValue]
        """Add ACM cert."""
        if self.acm_certificate_specified:
            return cloudfront.ViewerCertificate(
                AcmCertificateArn=self.get_variables()["AcmCertificateArn"],
                SslSupportMethod="sni-only",
            )
        return NoValue

    def add_origin_access_identity(self):
        # type: () -> cloudfront.CloudFrontOriginAccessIdentity
        """Add the origin access identity resource to the template.

        Returns:
            The OAI resource

        """
        return self.template.add_resource(
            cloudfront.CloudFrontOriginAccessIdentity(
                "OAI",
                CloudFrontOriginAccessIdentityConfig=cloudfront.CloudFrontOriginAccessIdentityConfig(  # noqa
                    Comment="CF access to website"
                ),
            )
        )

    def add_bucket_policy(self, bucket):
        # type: (s3.Bucket) -> s3.BucketPolicy
        """Add a policy to the bucket if CloudFront is disabled. Ensure PublicRead.

        Args:
            bucket: The bucket resource to place the policy.

        Returns:
            The Bucket Policy Resource.

        """
        return self.template.add_resource(
            s3.BucketPolicy(
                "BucketPolicy",
                Bucket=bucket.ref(),
                PolicyDocument=Policy(
                    Version="2012-10-17",
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Principal=Principal("*"),
                            Action=[Action("s3", "getObject")],
                            Resource=[Join("", [bucket.get_att("Arn"), "/*"])],
                        )
                    ],
                ),
            )
        )

    def add_bucket(self):
        # type: () -> s3.Bucket
        """Add the bucket resource along with an output of it's name / website url.

        Returns:
            The bucket resource.

        """
        bucket = self.template.add_resource(
            s3.Bucket(
                "Bucket",
                AccessControl=(s3.Private if self.cf_enabled else s3.PublicRead),
                LifecycleConfiguration=s3.LifecycleConfiguration(
                    Rules=[
                        s3.LifecycleRule(
                            NoncurrentVersionExpirationInDays=90, Status="Enabled"
                        )
                    ]
                ),
                VersioningConfiguration=s3.VersioningConfiguration(Status="Enabled"),
                WebsiteConfiguration=s3.WebsiteConfiguration(
                    IndexDocument="index.html", ErrorDocument="error.html"
                ),
            )
        )
        self.template.add_output(
            Output(
                "BucketName", Description="Name of website bucket", Value=bucket.ref()
            )
        )

        if not self.cf_enabled:
            self.template.add_output(
                Output(
                    "BucketWebsiteURL",
                    Description="URL of the bucket website",
                    Value=bucket.get_att("WebsiteURL"),
                )
            )

        return bucket

    def add_cloudfront_bucket_policy(self, bucket, oai):
        # type (s3.Bucket, cloudfront.CloudFrontOriginAccessIdentity) -> s3.BucketPolicy
        """Given a bucket and oai resource add cloudfront access to the bucket.

        Keyword Args:
            bucket: A bucket resource.
            oai: An Origin Access Identity resource.

        Return:
            The CloudFront Bucket access resource.

        """
        return self.template.add_resource(
            s3.BucketPolicy(
                "AllowCFAccess",
                Bucket=bucket.ref(),
                PolicyDocument=PolicyDocument(
                    Version="2012-10-17",
                    Statement=self._get_cloudfront_bucket_policy_statements(
                        bucket, oai
                    ),
                ),
            )
        )

    def add_lambda_execution_role(
        self,
        name="LambdaExecutionRole",  # type: str
        function_name="",  # type: str
    ):  # noqa: E124
        # type: (...) -> iam.Role
        """Create the Lambda@Edge execution role.

        Args:
            name: Name for the Lambda Execution Role.
            function_name: Name of the Lambda Function the Role will be
                attached to.

        """
        variables = self.get_variables()

        lambda_resource = Join(
            "",
            [
                "arn:",
                Partition,
                ":logs:*:",
                AccountId,
                ":log-group:/aws/lambda/",
                StackName,
                "-%s-*" % function_name,
            ],
        )

        edge_resource = Join(
            "",
            [
                "arn:",
                Partition,
                ":logs:*:",
                AccountId,
                ":log-group:/aws/lambda/*.",
                StackName,
                "-%s-*" % function_name,
            ],
        )

        return self.template.add_resource(
            iam.Role(
                name,
                AssumeRolePolicyDocument=make_simple_assume_policy(
                    "lambda.amazonaws.com", "edgelambda.amazonaws.com"
                ),
                PermissionsBoundary=(
                    variables["RoleBoundaryArn"]
                    if self.role_boundary_specified
                    else NoValue
                ),
                Policies=[
                    iam.Policy(
                        PolicyName="LambdaLogCreation",
                        PolicyDocument=PolicyDocument(
                            Version="2012-10-17",
                            Statement=[
                                Statement(
                                    Action=[
                                        awacs.logs.CreateLogGroup,
                                        awacs.logs.CreateLogStream,
                                        awacs.logs.PutLogEvents,
                                    ],
                                    Effect=Allow,
                                    Resource=[lambda_resource, edge_resource],
                                )
                            ],
                        ),
                    ),
                ],
            )
        )

    def add_cloudfront_directory_index_rewrite(self, role):
        # type: (iam.Role) -> awslambda.Function
        """Add an index CloudFront directory index rewrite lambda function to the template.

        Keyword Args:
            role: The index rewrite role resource.

        Return:
            The CloudFront directory index rewrite lambda function resource.

        """
        variables = self.get_variables()
        code_str = ""
        path = os.path.join(
            os.path.dirname(__file__),
            "templates/cf_directory_index_rewrite.template.js",
        )
        with open(path) as file_:
            code_str = file_.read().replace(
                "{{RewriteDirectoryIndex}}", variables["RewriteDirectoryIndex"]
            )

        function = self.template.add_resource(
            awslambda.Function(
                "CFDirectoryIndexRewrite",
                Code=awslambda.Code(ZipFile=code_str),
                DeletionPolicy="Retain",
                Description="Rewrites CF directory HTTP requests to default page",
                Handler="index.handler",
                Role=role.get_att("Arn"),
                Runtime="nodejs10.x",
            )
        )

        self.template.add_output(
            Output(
                "LambdaCFDirectoryIndexRewriteArn",
                Description="Directory Index Rewrite Function Arn",
                Value=function.get_att("Arn"),
            )
        )

        return function

    def add_cloudfront_directory_index_rewrite_version(self, directory_index_rewrite):
        # type: (awslambda.Function) -> awslambda.Version
        """Add a specific version to the directory index rewrite lambda.

        Args:
            directory_index_rewrite (dict): The directory index rewrite lambda resource.

        Return:
            dict: The CloudFront directory index rewrite version.

        """
        code_hash = hashlib.md5(
            str(
                directory_index_rewrite.properties["Code"].properties["ZipFile"]
            ).encode()
        ).hexdigest()

        return self.template.add_resource(
            awslambda.Version(
                "CFDirectoryIndexRewriteVer" + code_hash,
                FunctionName=directory_index_rewrite.ref(),
            )
        )

    def add_cloudfront_distribution(
        self, bucket_policy, cloudfront_distribution_options
    ):
        # type: (s3.BucketPolicy, Dict[str, Any]) -> cloudfront.Distribution
        """Add the CloudFront distribution to the template / output the id and domain name.

        Args:
            bucket_policy (dict): Bucket policy to allow CloudFront access.
            cloudfront_distribution_options (dict): The distribution options.

        Return:
            dict: The CloudFront Distribution resource

        """
        distribution = self.template.add_resource(
            cloudfront.Distribution(
                "CFDistribution",
                DependsOn=bucket_policy.title,
                DistributionConfig=cloudfront.DistributionConfig(
                    **cloudfront_distribution_options
                ),
            )
        )
        self.template.add_output(
            Output(
                "CFDistributionId",
                Description="CloudFront distribution ID",
                Value=distribution.ref(),
            )
        )
        self.template.add_output(
            Output(
                "CFDistributionDomainName",
                Description="CloudFront distribution domain name",
                Value=distribution.get_att("DomainName"),
            )
        )
        return distribution

    def _get_cloudfront_bucket_policy_statements(  # pylint: disable=no-self-use
        self, bucket, oai
    ):
        return [
            Statement(
                Action=[awacs.s3.GetObject],
                Effect=Allow,
                Principal=Principal("CanonicalUser", oai.get_att("S3CanonicalUserId")),
                Resource=[Join("", [bucket.get_att("Arn"), "/*"])],
            )
        ]

    def _get_index_rewrite_role_function_and_version(self):
        res = {}
        res["role"] = self.add_lambda_execution_role(
            "CFDirectoryIndexRewriteRole", "CFDirectoryIndexRewrite"
        )
        res["function"] = self.add_cloudfront_directory_index_rewrite(res["role"])
        res["version"] = self.add_cloudfront_directory_index_rewrite_version(
            res["function"]
        )
        return res


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    print(StaticSite("test", Context({"namespace": "test"}), None).to_json())
