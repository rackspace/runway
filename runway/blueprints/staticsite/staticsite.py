#!/usr/bin/env python
"""Module with static website bucket and CloudFront distribution."""
from __future__ import annotations

import hashlib
import logging
import os
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Union

import awacs.awslambda
import awacs.iam
import awacs.logs
import awacs.s3
import awacs.states
import awacs.sts
from awacs.aws import Action, Allow, Policy, PolicyDocument, Principal, Statement
from awacs.helpers.trust import make_simple_assume_policy
from troposphere import (
    AccountId,
    Join,
    NoValue,
    Output,
    Partition,
    Region,
    StackName,
    awslambda,
    cloudfront,
    iam,
    s3,
)
from typing_extensions import TypedDict

from ...cfngin.blueprints.base import Blueprint
from ...context import CfnginContext

if TYPE_CHECKING:
    from troposphere import Ref  # pylint: disable=ungrouped-imports

    from ...cfngin.blueprints.type_defs import BlueprintVariableTypeDef

LOGGER = logging.getLogger("runway")

IAM_ARN_PREFIX = "arn:aws:iam::aws:policy/service-role/"


class _IndexRewriteFunctionInfoTypeDef(TypedDict, total=False):

    function: awslambda.Function
    role: iam.Role
    version: awslambda.Version


class StaticSite(Blueprint):
    """CFNgin blueprint for creating S3 bucket and CloudFront distribution."""

    VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
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
        "Compress": {
            "type": bool,
            "default": True,
            "description": "Whether the CloudFront default cache behavior will "
            "automatically compress certain files.",
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
    def aliases_specified(self) -> bool:
        """Aliases are specified conditional."""
        return self.variables["Aliases"] != [""]

    @property
    def cf_enabled(self) -> bool:
        """CloudFront enabled conditional."""
        return not self.variables.get("DisableCloudFront", False)

    @property
    def acm_certificate_specified(self) -> bool:
        """ACM Certification specified conditional."""
        return self.variables["AcmCertificateArn"] != ""

    @property
    def cf_logging_enabled(self) -> bool:
        """CloudFront Logging specified conditional."""
        return self.variables["LogBucketName"] != ""

    @property
    def directory_index_specified(self) -> bool:
        """Directory Index specified conditional."""
        return self.variables["RewriteDirectoryIndex"] != ""

    @property
    def role_boundary_specified(self) -> bool:
        """IAM Role Boundary specified conditional."""
        return self.variables["RoleBoundaryArn"] != ""

    @property
    def waf_name_specified(self) -> bool:
        """WAF name specified conditional."""
        return self.variables["WAFWebACL"] != ""

    def create_template(self) -> None:
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
                lambda_function_associations = (
                    self.get_directory_index_lambda_association(
                        lambda_function_associations, index_rewrite.get("version", "")
                    )
                )

            distribution_options = self.get_cloudfront_distribution_options(
                bucket, oai, lambda_function_associations
            )
            self.add_cloudfront_distribution(bucket_policy, distribution_options)
        else:
            self.add_bucket_policy(bucket)

    def get_lambda_associations(self) -> List[cloudfront.LambdaFunctionAssociation]:
        """Retrieve any lambda associations from the instance variables."""
        # If custom associations defined, use them
        if self.variables["lambda_function_associations"]:
            return [
                cloudfront.LambdaFunctionAssociation(
                    EventType=x["type"], LambdaFunctionARN=x["arn"]
                )
                for x in self.variables["lambda_function_associations"]
            ]
        return []

    @staticmethod
    def get_directory_index_lambda_association(
        lambda_associations: List[cloudfront.LambdaFunctionAssociation],
        directory_index_rewrite_version: awslambda.Version,
    ) -> List[cloudfront.LambdaFunctionAssociation]:
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
        bucket: s3.Bucket,
        oai: cloudfront.CloudFrontOriginAccessIdentity,
        lambda_function_associations: List[cloudfront.LambdaFunctionAssociation],
    ) -> Dict[str, Any]:
        """Retrieve the options for our CloudFront distribution.

        Args:
            bucket: The bucket resource
            oai: The origin access identity resource.
            lambda_function_associations: List of Lambda Function associations.

        Return:
            The CloudFront Distribution Options.

        """
        if os.getenv("AWS_REGION") == "us-east-1":
            # use global endpoint for us-east-1
            origin = Join(".", [bucket.ref(), "s3.amazonaws.com"])
        else:
            # use reginal endpoint to avoid "temporary" redirect that can last over an hour
            # https://forums.aws.amazon.com/message.jspa?messageID=677452
            origin = Join(".", [bucket.ref(), "s3", Region, "amazonaws.com"])

        return {
            "Aliases": self.add_aliases(),
            "Origins": [
                cloudfront.Origin(
                    DomainName=origin,
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
                Compress=self.variables.get("Compress", True),
                DefaultTTL="86400",
                ForwardedValues=cloudfront.ForwardedValues(
                    Cookies=cloudfront.Cookies(Forward="none"), QueryString=False
                ),
                LambdaFunctionAssociations=lambda_function_associations,
                TargetOriginId="S3Origin",
                ViewerProtocolPolicy="redirect-to-https",
            ),
            "DefaultRootObject": "index.html",
            "Logging": self.add_logging_bucket(),
            "PriceClass": self.variables["PriceClass"],
            "CustomErrorResponses": [
                cloudfront.CustomErrorResponse(
                    ErrorCode=response["ErrorCode"],
                    ResponseCode=response["ResponseCode"],
                    ResponsePagePath=response["ResponsePagePath"],
                )
                for response in self.variables["custom_error_responses"]
            ],
            "Enabled": True,
            "WebACLId": self.add_web_acl(),
            "ViewerCertificate": self.add_acm_cert(),
        }

    def add_aliases(self) -> Union[List[str], Ref]:
        """Add aliases."""
        if self.aliases_specified:
            return self.variables["Aliases"]
        return NoValue

    def add_web_acl(self) -> Union[str, Ref]:
        """Add Web ACL."""
        if self.waf_name_specified:
            return self.variables["WAFWebACL"]
        return NoValue

    def add_logging_bucket(self) -> Union[cloudfront.Logging, Ref]:
        """Add Logging Bucket."""
        if self.cf_logging_enabled:
            return cloudfront.Logging(
                Bucket=Join(".", [self.variables["LogBucketName"], "s3.amazonaws.com"])
            )
        return NoValue

    def add_acm_cert(self) -> Union[cloudfront.ViewerCertificate, Ref]:
        """Add ACM cert."""
        if self.acm_certificate_specified:
            return cloudfront.ViewerCertificate(
                AcmCertificateArn=self.variables["AcmCertificateArn"],
                SslSupportMethod="sni-only",
            )
        return NoValue

    def add_origin_access_identity(self) -> cloudfront.CloudFrontOriginAccessIdentity:
        """Add the origin access identity resource to the template."""
        return self.template.add_resource(
            cloudfront.CloudFrontOriginAccessIdentity(
                "OAI",
                CloudFrontOriginAccessIdentityConfig=cloudfront.CloudFrontOriginAccessIdentityConfig(  # noqa
                    Comment="CF access to website"
                ),
            )
        )

    def add_bucket_policy(self, bucket: s3.Bucket) -> s3.BucketPolicy:
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

    def add_bucket(self) -> s3.Bucket:
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
            )
        )
        self.template.add_output(
            Output(
                "BucketName", Description="Name of website bucket", Value=bucket.ref()
            )
        )

        if not self.cf_enabled:
            # bucket cannot be configured with WebsiteConfiguration when using OAI S3Origin
            bucket.WebsiteConfiguration = s3.WebsiteConfiguration(
                IndexDocument="index.html", ErrorDocument="error.html"
            )
            self.template.add_output(
                Output(
                    "BucketWebsiteURL",
                    Description="URL of the bucket website",
                    Value=bucket.get_att("WebsiteURL"),
                )
            )

        return bucket

    def add_cloudfront_bucket_policy(
        self, bucket: s3.Bucket, oai: cloudfront.CloudFrontOriginAccessIdentity
    ) -> s3.BucketPolicy:
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
        self, name: str = "LambdaExecutionRole", function_name: str = ""
    ) -> iam.Role:
        """Create the Lambda@Edge execution role.

        Args:
            name: Name for the Lambda Execution Role.
            function_name: Name of the Lambda Function the Role will be
                attached to.

        """
        lambda_resource = Join(
            "",
            [
                "arn:",
                Partition,
                ":logs:*:",
                AccountId,
                ":log-group:/aws/lambda/",
                StackName,
                f"-{function_name}-*",
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
                f"-{function_name}-*",
            ],
        )

        return self.template.add_resource(
            iam.Role(
                name,
                AssumeRolePolicyDocument=make_simple_assume_policy(
                    "lambda.amazonaws.com", "edgelambda.amazonaws.com"
                ),
                PermissionsBoundary=(
                    self.variables["RoleBoundaryArn"]
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

    def add_cloudfront_directory_index_rewrite(
        self, role: iam.Role
    ) -> awslambda.Function:
        """Add an index CloudFront directory index rewrite lambda function to the template.

        Keyword Args:
            role: The index rewrite role resource.

        Return:
            The CloudFront directory index rewrite lambda function resource.

        """
        code_str = ""
        path = os.path.join(
            os.path.dirname(__file__),
            "templates/cf_directory_index_rewrite.template.js",
        )
        with open(path, encoding="utf-8") as file_:
            code_str = file_.read().replace(
                "{{RewriteDirectoryIndex}}", self.variables["RewriteDirectoryIndex"]
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

    def add_cloudfront_directory_index_rewrite_version(
        self, directory_index_rewrite: awslambda.Function
    ) -> awslambda.Version:
        """Add a specific version to the directory index rewrite lambda.

        Args:
            directory_index_rewrite: The directory index rewrite lambda resource.

        Return:
            The CloudFront directory index rewrite version.

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
        self,
        bucket_policy: s3.BucketPolicy,
        cloudfront_distribution_options: Dict[str, Any],
    ) -> cloudfront.Distribution:
        """Add the CloudFront distribution to the template / output the id and domain name.

        Args:
            bucket_policy: Bucket policy to allow CloudFront access.
            cloudfront_distribution_options: The distribution options.

        Return:
            The CloudFront Distribution resource

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

    @staticmethod
    def _get_cloudfront_bucket_policy_statements(
        bucket: s3.Bucket, oai: cloudfront.CloudFrontOriginAccessIdentity
    ) -> List[Statement]:
        return [
            Statement(
                Action=[awacs.s3.GetObject],
                Effect=Allow,
                # S3CanonicalUserId is translated to the ARN when AWS renders this
                Principal=Principal("CanonicalUser", oai.get_att("S3CanonicalUserId")),
                Resource=[Join("", [bucket.get_att("Arn"), "/*"])],
            )
        ]

    def _get_index_rewrite_role_function_and_version(
        self,
    ) -> _IndexRewriteFunctionInfoTypeDef:
        res: _IndexRewriteFunctionInfoTypeDef = {
            "role": self.add_lambda_execution_role(
                "CFDirectoryIndexRewriteRole", "CFDirectoryIndexRewrite"
            )
        }

        res["function"] = self.add_cloudfront_directory_index_rewrite(
            res.get("role", "")
        )
        res["version"] = self.add_cloudfront_directory_index_rewrite_version(
            res.get("function", "")
        )
        return res


# Helper section to enable easy blueprint -> template generation
# (just run `python <thisfile>` to output the json)
if __name__ == "__main__":
    print(  # noqa: T001
        StaticSite("test", CfnginContext(parameters={"namespace": "test"})).to_json()
    )
