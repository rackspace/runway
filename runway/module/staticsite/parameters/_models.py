"""Runway static site Module parameters."""

from __future__ import annotations

from pydantic import ConfigDict, Field, field_validator

from ....config.models.base import ConfigProperty


class RunwayStaticSiteCustomErrorResponseDataModel(ConfigProperty):
    """Model for Runway stat site Module staticsite_custom_error_responses parameter item.

    https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distribution-customerrorresponse.html

    """

    model_config = ConfigDict(
        extra="forbid",
        title="Runway static site Module staticsite_custom_error_responses parameter item",
        validate_default=True,
        validate_assignment=True,
    )

    ErrorCachingMinTTL: int | None = None
    ErrorCode: int | None = None
    ResponseCode: int | None = None
    ResponsePagePath: str | None = None


class RunwayStaticSiteLambdaFunctionAssociationDataModel(ConfigProperty):
    """Model for Runway stat site Module staticsite_lambda_function_associations parameter item."""

    model_config = ConfigDict(
        extra="forbid",
        title="Runway static site Module staticsite_lambda_function_associations parameter item",
        validate_default=True,
        validate_assignment=True,
    )

    arn: str
    """Lambda function ARN."""

    type: str
    """Association type."""


def _staticsite_alias_generator(field_name: str) -> str:
    """Append ``staticsite`` to field names.

    Some fields are excluded from having aliases (e.g. namespace).

    """
    return f"staticsite_{field_name}" if field_name != "namespace" else field_name


class RunwayStaticSiteModuleParametersDataModel(ConfigProperty):
    """Model for Runway static site Module parameters."""

    model_config = ConfigDict(
        alias_generator=_staticsite_alias_generator,
        extra="ignore",
        populate_by_name=True,
        title="Runway static site Module parameters",
        validate_default=True,
        validate_assignment=True,
    )

    acmcert_arn: str | None = None
    """The certificate arn used for any alias domains supplied.
    This is a requirement when supplying any custom domain.

    """

    additional_redirect_domains: list[str] = []
    """Additional domains (beyond the ``aliases`` domains or the CloudFront URL if
    no aliases are provided) that will be authorized by the Auth@Edge UserPool AppClient.

    """

    aliases: list[str] = []
    """Any custom domains that should be added to the CloudFront Distribution."""

    cf_disable: bool = False
    """Whether deployment of the CloudFront Distribution should be disabled."""

    compress: bool = True
    """Whether the CloudFront default cache behavior will automatically compress certain files."""

    cookie_settings: dict[str, str] = {
        "idToken": "Path=/; Secure; SameSite=Lax",
        "accessToken": "Path=/; Secure; SameSite=Lax",
        "refreshToken": "Path=/; Secure; SameSite=Lax",
        "nonce": "Path=/; Secure; HttpOnly; Max-Age=1800; SameSite=Lax",
    }
    """The default cookie settings for retrieved tokens and generated nonce's."""

    custom_error_responses: list[RunwayStaticSiteCustomErrorResponseDataModel] = []
    """Define custom error responses."""

    enable_cf_logging: bool = True
    """Enable CloudFront logging."""

    http_headers: dict[str, str] = {
        "Content-Security-Policy": "default-src https: 'unsafe-eval' 'unsafe-inline'; "
        "font-src 'self' 'unsafe-inline' 'unsafe-eval' data: https:; "
        "object-src 'none'; "
        "connect-src 'self' https://*.amazonaws.com https://*.amazoncognito.com",
        "Strict-Transport-Security": "max-age=31536000; includeSubdomains; preload",
        "Referrer-Policy": "same-origin",
        "X-XSS-Protection": "1; mode=block",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
    }
    """Headers that should be sent with each origin response."""

    lambda_function_associations: list[RunwayStaticSiteLambdaFunctionAssociationDataModel] = []
    """This allows the user to deploy custom Lambda@Edge associations with their pre-build function versions."""

    namespace: str
    """The unique namespace for the deployment."""

    non_spa: bool = False
    """Whether this site is a single page application (SPA)."""

    rewrite_directory_index: str | None = None
    """Deploy a Lambda@Edge function designed to rewrite directory indexes."""

    role_boundary_arn: str | None = None
    """Defines an IAM Managed Policy that will be set as the permissions boundary
    for any IAM Roles created to support the site.

    """

    service_role: str | None = Field(default=None, alias="cloudformation_service_role")
    """IAM role that CloudFormation will use."""

    web_acl: str | None = None
    """The ARN of a web access control list (web ACL) to associate with the CloudFront Distribution."""

    @field_validator(
        "additional_redirect_domains",
        "aliases",
        mode="before",
    )
    @classmethod
    def _convert_comma_delimited_list(cls, v: list[str] | str) -> list[str]:
        """Convert comma delimited lists to a string."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
