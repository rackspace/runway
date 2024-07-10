"""Test runway.module.staticsite.parameters.models."""

# pyright: basic
from typing import Any, Dict, cast

import pytest
from pydantic import ValidationError

from runway.module.staticsite.parameters.models import (
    RunwayStaticSiteCustomErrorResponseDataModel,
    RunwayStaticSiteLambdaFunctionAssociationDataModel,
    RunwayStaticSiteModuleParametersDataModel,
)

MODULE = "runway.module.staticsite.parameters.models"


class TestRunwayStaticSiteCustomErrorResponseDataModel:
    """Test RunwayStaticSiteCustomErrorResponseDataModel."""

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayStaticSiteCustomErrorResponseDataModel()
        assert not obj.ErrorCachingMinTTL
        assert not obj.ErrorCode
        assert not obj.ResponseCode
        assert not obj.ResponsePagePath

    def test_init_extra(self) -> None:
        """Test init extra."""
        with pytest.raises(ValidationError):
            RunwayStaticSiteCustomErrorResponseDataModel(invalid="val")  # type: ignore

    def test_init(self) -> None:
        """Test init."""
        data = {
            "ErrorCachingMinTTL": 30,
            "ErrorCode": 404,
            "ResponseCode": 404,
            "ResponsePagePath": "./errors/404.html",
        }
        obj = RunwayStaticSiteCustomErrorResponseDataModel(**data)
        assert obj.ErrorCachingMinTTL == data["ErrorCachingMinTTL"]
        assert obj.ErrorCode == data["ErrorCode"]
        assert obj.ResponseCode == data["ResponseCode"]
        assert obj.ResponsePagePath == data["ResponsePagePath"]


class TestRunwayStaticSiteLambdaFunctionAssociationDataModel:
    """Test RunwayStaticSiteLambdaFunctionAssociationDataModel."""

    def test_init_extra(self) -> None:
        """Test init extra."""
        with pytest.raises(ValidationError):
            RunwayStaticSiteLambdaFunctionAssociationDataModel(invalid="val")  # type: ignore

    @pytest.mark.parametrize(
        "data",
        [
            cast(Dict[str, Any], {}),
            {"arn": "aws:arn:lambda:us-east-1:function:test"},
            {"type": "origin-request"},
        ],
    )
    def test_init_required(self, data: Dict[str, Any]) -> None:
        """Test init required."""
        with pytest.raises(ValidationError):
            RunwayStaticSiteLambdaFunctionAssociationDataModel.parse_obj(data)

    def test_init(self) -> None:
        """Test init."""
        data = {
            "arn": "aws:arn:lambda:us-east-1:function:test",
            "type": "origin-request",
        }
        obj = RunwayStaticSiteLambdaFunctionAssociationDataModel(**data)
        assert obj.arn == data["arn"]
        assert obj.type == data["type"]


class TestRunwayStaticSiteModuleParametersDataModel:
    """Test RunwayStaticSiteModuleParametersDataModel."""

    def test_convert_comma_delimited_list(self) -> None:
        """Test _convert_comma_delimited_list."""
        obj = RunwayStaticSiteModuleParametersDataModel(
            namespace="test",
            staticsite_additional_redirect_domains="redirect0,redirect1",  # type: ignore
            staticsite_aliases="test-alias",  # type: ignore
            staticsite_supported_identity_providers="id0, id1",  # type: ignore
        )
        assert obj.additional_redirect_domains == ["redirect0", "redirect1"]
        assert obj.aliases == ["test-alias"]
        assert obj.supported_identity_providers == ["id0", "id1"]

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayStaticSiteModuleParametersDataModel(namespace="test")
        assert not obj.acmcert_arn
        assert obj.additional_redirect_domains == []
        assert obj.aliases == []
        assert obj.auth_at_edge is False
        assert obj.cf_disable is False
        assert obj.cookie_settings == {
            "idToken": "Path=/; Secure; SameSite=Lax",
            "accessToken": "Path=/; Secure; SameSite=Lax",
            "refreshToken": "Path=/; Secure; SameSite=Lax",
            "nonce": "Path=/; Secure; HttpOnly; Max-Age=1800; SameSite=Lax",
        }
        assert obj.create_user_pool is False
        assert obj.custom_error_responses == []
        assert obj.enable_cf_logging is True
        assert obj.http_headers == {
            "Content-Security-Policy": "default-src https: 'unsafe-eval' 'unsafe-inline'; "
            "font-src 'self' 'unsafe-inline' 'unsafe-eval' data: https:; "
            "object-src 'none'; "
            "connect-src 'self' https://*.amazonaws.com https://*.amazoncognito.com",
            "Strict-Transport-Security": "max-age=31536000; " "includeSubdomains; " "preload",
            "Referrer-Policy": "same-origin",
            "X-XSS-Protection": "1; mode=block",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
        }
        assert obj.lambda_function_associations == []
        assert obj.namespace == "test"
        assert obj.non_spa is False
        assert obj.oauth_scopes == [
            "phone",
            "email",
            "profile",
            "openid",
            "aws.cognito.signin.user.admin",
        ]
        assert obj.redirect_path_auth_refresh == "/refreshauth"
        assert obj.redirect_path_sign_in == "/parseauth"
        assert obj.redirect_path_sign_out == "/"
        assert not obj.required_group
        assert not obj.rewrite_directory_index
        assert not obj.role_boundary_arn
        assert not obj.service_role
        assert obj.sign_out_url == "/signout"
        assert obj.supported_identity_providers == ["COGNITO"]
        assert not obj.user_pool_arn
        assert not obj.web_acl

    def test_init_extra(self) -> None:
        """Test init extra."""
        obj = RunwayStaticSiteModuleParametersDataModel(
            namespace="test", invalid="val"  # type: ignore
        )
        assert "invalid" not in obj.dict()

    def test_init_required(self) -> None:
        """Test init required."""
        with pytest.raises(ValidationError):
            RunwayStaticSiteModuleParametersDataModel.parse_obj({})

    def test_init(self) -> None:
        """Test init."""
        data = {
            "cloudformation_service_role": "aws:arn:iam:123456789012:role/name",
            "staticsite_acmcert_arn": "aws:arn:acm:us-east-1:cert:test",
            "staticsite_additional_redirect_domains": ["github.com"],
            "staticsite_aliases": ["test-alias"],
            "staticsite_auth_at_edge": True,
            "staticsite_cf_disable": True,
            "staticsite_cookie_settings": {"test-cookie": "val"},
            "staticsite_create_user_pool": True,
            "staticsite_custom_error_responses": [{"ErrorCode": 404}],
            "staticsite_enable_cf_logging": False,
            "staticsite_http_headers": {"test-header": "val"},
            "staticsite_lambda_function_associations": [
                {
                    "arn": "aws:arn:lambda:us-east-1:function:test",
                    "type": "origin-request",
                }
            ],
            "namespace": "test",
            "staticsite_non_spa": True,
            "staticsite_oauth_scopes": ["email"],
            "staticsite_redirect_path_auth_refresh": "/test-refresh",
            "staticsite_redirect_path_sign_in": "/test-sign-in",
            "staticsite_redirect_path_sign_out": "/test-sign-out-redirect",
            "staticsite_required_group": "any",
            "staticsite_rewrite_directory_index": "test-rewrite-index",
            "staticsite_role_boundary_arn": "arn:aws:iam:::role/test",
            "staticsite_sign_out_url": "/test-sign-out",
            "staticsite_supported_identity_providers": ["google"],
            "staticsite_user_pool_arn": "arn:aws:cognito:::pool/test",
            "staticsite_web_acl": "arn:aws::::acl/test",
        }
        obj = RunwayStaticSiteModuleParametersDataModel(**data)  # type: ignore
        assert obj.acmcert_arn == data["staticsite_acmcert_arn"]
        assert obj.additional_redirect_domains == data["staticsite_additional_redirect_domains"]
        assert obj.aliases == data["staticsite_aliases"]
        assert obj.auth_at_edge is data["staticsite_auth_at_edge"]
        assert obj.cf_disable is data["staticsite_cf_disable"]
        assert obj.cookie_settings == data["staticsite_cookie_settings"]
        assert obj.create_user_pool is data["staticsite_create_user_pool"]
        assert len(obj.custom_error_responses) == len(
            data["staticsite_custom_error_responses"]  # type: ignore
        )
        assert (
            obj.custom_error_responses[0].dict(exclude_none=True)
            == data["staticsite_custom_error_responses"][0]  # type: ignore
        )
        assert obj.enable_cf_logging is data["staticsite_enable_cf_logging"]
        assert obj.http_headers == data["staticsite_http_headers"]
        assert len(obj.lambda_function_associations) == len(
            data["staticsite_lambda_function_associations"]  # type: ignore
        )
        assert (
            obj.lambda_function_associations[0].dict()
            == data["staticsite_lambda_function_associations"][0]  # type: ignore
        )
        assert obj.namespace == data["namespace"]
        assert obj.non_spa is data["staticsite_non_spa"]
        assert obj.oauth_scopes == data["staticsite_oauth_scopes"]
        assert obj.redirect_path_auth_refresh == data["staticsite_redirect_path_auth_refresh"]
        assert obj.redirect_path_sign_in == data["staticsite_redirect_path_sign_in"]
        assert obj.redirect_path_sign_out == data["staticsite_redirect_path_sign_out"]
        assert obj.required_group == data["staticsite_required_group"]
        assert obj.rewrite_directory_index == data["staticsite_rewrite_directory_index"]
        assert obj.role_boundary_arn == data["staticsite_role_boundary_arn"]
        assert obj.service_role == data["cloudformation_service_role"]
        assert obj.sign_out_url == data["staticsite_sign_out_url"]
        assert obj.supported_identity_providers == data["staticsite_supported_identity_providers"]
        assert obj.user_pool_arn == data["staticsite_user_pool_arn"]
        assert obj.web_acl == data["staticsite_web_acl"]
