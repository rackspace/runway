"""Runway static site Module parameters."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

from typing import Dict, List, Optional, Union

from pydantic import Extra, Field, validator

from ....config.models.base import ConfigProperty


class RunwayStaticSiteCustomErrorResponseDataModel(ConfigProperty):
    """Model for Runway stat site Module staticsite_custom_error_responses parameter item.

    https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distribution-customerrorresponse.html

    """

    ErrorCachingMinTTL: Optional[int] = None
    ErrorCode: Optional[int] = None
    ResponseCode: Optional[int] = None
    ResponsePagePath: Optional[str] = None

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        title = "Runway static site Module staticsite_custom_error_responses parameter item."


class RunwayStaticSiteLambdaFunctionAssociationDataModel(ConfigProperty):
    """Model for Runway stat site Module staticsite_lambda_function_associations parameter item.

    Attributes:
        arn: Lambda function ARN.
        type: Association type.

    """

    arn: str
    type: str

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        title = "Runway static site Module staticsite_lambda_function_associations parameter item."  # noqa


class RunwayStaticSiteModuleParametersDataModel(ConfigProperty):
    """Model for Runway static site Module parameters.

    Attributes:
        acmcert_arn: The certificate arn used for any alias domains supplied.
            This is a requirement when supplying any custom domain.
        additional_redirect_domains: Additional domains (beyond the ``aliases``
            domains or the CloudFront URL if no aliases are provided) that will
            be authorized by the Auth@Edge UserPool AppClient.
        aliases: Any custom domains that should be added to the CloudFront
            Distribution.
        auth_at_edge: Auth@Edge make the static site private by placing it behind
            an authorization wall.
        cf_disable: Wether deployment of the CloudFront Distribution should be
            disabled.
        compress: Whether the CloudFront default cache behavior will automatically
            compress certain files.
        cookie_settings: The default cookie settings for retrieved tokens and
            generated nonce’s.
        create_user_pool: Wether to create a User Pool for the Auth@Edge
            configuration.
        custom_error_responses: Define custom error responses.
        enable_cf_logging: Enable CloudFront logging.
        http_headers: Headers that should be sent with each origin response.
        lambda_function_associations: This allows the user to deploy custom
            Lambda@Edge associations with their pre-build function versions.
        namespace: The unique namespace for the deployment.
        non_spa: Wether this site is a single page application (SPA).
        oauth_scopes: Scope is a mechanism in OAuth 2.0 to limit an application’s
            access to a user’s account.
        redirect_path_auth_refresh: The path that a user is redirected to when
            their authorization tokens have expired (1 hour).
        redirect_path_sign_in: The path that a user is redirected to after sign-in.
        redirect_path_sign_out: The path that a user is redirected to after sign-out.
        required_group: Name of Cognito User Pool group of which users must be a
            member to be granted access to the site. If ``None``, allows all
            UserPool users to have access.
        rewrite_directory_index: Deploy a Lambda@Edge function designed to
            rewrite directory indexes.
        role_boundary_arn: Defines an IAM Managed Policy that will be set as the
            permissions boundary for any IAM Roles created to support the site.
        service_role: IAM role that CloudFormation will use.
        sign_out_url: The path a user should access to sign themselves out of the
            application.
        supported_identity_providers: A comma delimited list of the User Pool
            client identity providers.
        user_pool_arn: The ARN of a pre-existing Cognito User Pool to use with
            Auth@Edge.
        web_acl: The ARN of a web access control list (web ACL) to associate with
            the CloudFront Distribution.

    """

    acmcert_arn: Optional[str] = Field(None, alias="staticsite_acmcert_arn")
    additional_redirect_domains: List[str] = Field(
        [], alias="staticsite_additional_redirect_domains"
    )
    aliases: List[str] = Field([], alias="staticsite_aliases")
    auth_at_edge: bool = Field(False, alias="staticsite_auth_at_edge")
    cf_disable: bool = Field(False, alias="staticsite_cf_disable")
    compress: bool = Field(True, alias="staticsite_compress")
    cookie_settings: Dict[str, str] = Field(
        {
            "idToken": "Path=/; Secure; SameSite=Lax",
            "accessToken": "Path=/; Secure; SameSite=Lax",
            "refreshToken": "Path=/; Secure; SameSite=Lax",
            "nonce": "Path=/; Secure; HttpOnly; Max-Age=1800; SameSite=Lax",
        },
        alias="staticsite_cookie_settings",
    )
    create_user_pool: bool = Field(False, alias="staticsite_create_user_pool")
    custom_error_responses: List[RunwayStaticSiteCustomErrorResponseDataModel] = Field(
        [], alias="staticsite_custom_error_responses"
    )
    enable_cf_logging: bool = Field(True, alias="staticsite_enable_cf_logging")
    http_headers: Dict[str, str] = Field(
        {
            "Content-Security-Policy": "default-src https: 'unsafe-eval' 'unsafe-inline'; "
            "font-src 'self' 'unsafe-inline' 'unsafe-eval' data: https:; "
            "object-src 'none'; "
            "connect-src 'self' https://*.amazonaws.com https://*.amazoncognito.com",
            "Strict-Transport-Security": "max-age=31536000; "
            "includeSubdomains; "
            "preload",
            "Referrer-Policy": "same-origin",
            "X-XSS-Protection": "1; mode=block",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
        },
        alias="staticsite_http_headers",
    )
    lambda_function_associations: List[
        RunwayStaticSiteLambdaFunctionAssociationDataModel
    ] = Field([], alias="staticsite_lambda_function_associations")
    namespace: str
    non_spa: bool = Field(False, alias="staticsite_non_spa")
    oauth_scopes: List[str] = Field(
        ["phone", "email", "profile", "openid", "aws.cognito.signin.user.admin"],
        alias="staticsite_oauth_scopes",
    )
    redirect_path_auth_refresh: str = Field(
        "/refreshauth", alias="staticsite_redirect_path_auth_refresh"
    )
    redirect_path_sign_in: str = Field(
        "/parseauth", alias="staticsite_redirect_path_sign_in"
    )
    redirect_path_sign_out: str = Field("/", alias="staticsite_redirect_path_sign_out")
    required_group: Optional[str] = Field(None, alias="staticsite_required_group")
    rewrite_directory_index: Optional[str] = Field(
        None, alias="staticsite_rewrite_directory_index"
    )
    role_boundary_arn: Optional[str] = Field(None, alias="staticsite_role_boundary_arn")
    service_role: Optional[str] = Field(None, alias="cloudformation_service_role")
    sign_out_url: str = Field("/signout", alias="staticsite_sign_out_url")
    supported_identity_providers: List[str] = Field(
        ["COGNITO"], alias="staticsite_supported_identity_providers"
    )
    user_pool_arn: Optional[str] = Field(None, alias="staticsite_user_pool_arn")
    web_acl: Optional[str] = Field(None, alias="staticsite_web_acl")

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.ignore
        title = "Runway static site Module parameters."

    @validator(
        "additional_redirect_domains",
        "aliases",
        "supported_identity_providers",
        pre=True,
    )
    def _convert_comma_delimited_list(cls, v: Union[List[str], str]) -> List[str]:
        """Convert comma delimited lists to a string."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
