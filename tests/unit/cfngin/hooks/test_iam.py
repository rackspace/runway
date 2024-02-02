"""Tests for runway.cfngin.hooks.iam."""

# pyright: basic
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from awacs.helpers.trust import get_ecs_assumerole_policy
from botocore.exceptions import ClientError

from runway.cfngin.hooks.iam import (
    ECS_SERVICE_ROLE_NAME,
    ECS_SERVICE_ROLE_POLICY,
    create_ecs_service_role,
    ensure_server_cert_exists,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from ...factories import MockCFNginContext

CREATE_DATE = datetime(2015, 1, 1)
MODULE = "runway.cfngin.hooks.iam"


def test_create_ecs_service_role(cfngin_context: MockCFNginContext) -> None:
    """Test create_ecs_service_role."""
    stub = cfngin_context.add_stubber("iam")

    stub.add_response(
        "create_role",
        {
            "Role": {  # data required by botocore.stub
                "Path": "/",
                "RoleName": ECS_SERVICE_ROLE_NAME,
                "RoleId": "0" * 16,
                "Arn": f"arn:aws:iam::0123456879012:role/{ECS_SERVICE_ROLE_NAME}",
                "CreateDate": CREATE_DATE,
            }
        },
        {
            "RoleName": ECS_SERVICE_ROLE_NAME,
            "AssumeRolePolicyDocument": get_ecs_assumerole_policy().to_json(),
        },
    )
    stub.add_response(
        "put_role_policy",
        {},
        {
            "RoleName": ECS_SERVICE_ROLE_NAME,
            "PolicyName": "AmazonEC2ContainerServiceRolePolicy",
            "PolicyDocument": ECS_SERVICE_ROLE_POLICY.to_json(),
        },
    )

    with stub:
        assert create_ecs_service_role(cfngin_context)
    stub.assert_no_pending_responses()


def test_create_ecs_service_role_already_exists(
    cfngin_context: MockCFNginContext,
) -> None:
    """Test create_ecs_service_role already exists."""
    stub = cfngin_context.add_stubber("iam")

    stub.add_client_error("create_role", service_message="already exists")
    stub.add_response(
        "put_role_policy",
        {},
        {
            "RoleName": ECS_SERVICE_ROLE_NAME,
            "PolicyName": "AmazonEC2ContainerServiceRolePolicy",
            "PolicyDocument": ECS_SERVICE_ROLE_POLICY.to_json(),
        },
    )

    with stub:
        assert create_ecs_service_role(cfngin_context)
    stub.assert_no_pending_responses()


def test_create_ecs_service_role_raise_client_error(
    cfngin_context: MockCFNginContext,
) -> None:
    """Test create_ecs_service_role raise ClientError."""
    stub = cfngin_context.add_stubber("iam")

    stub.add_client_error("create_role", service_message="")

    with stub, pytest.raises(ClientError):
        create_ecs_service_role(cfngin_context)
    stub.assert_no_pending_responses()


def test_ensure_server_cert_exists(
    cfngin_context: MockCFNginContext, mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test ensure_server_cert_exists."""
    cert_name = "foo"
    arn = f"arn:aws:iam::0123456789012:certification/{cert_name}"

    certificate_path = tmp_path / "cert"
    certificate_path.write_text("cert")

    chain_path = tmp_path / "chain"
    chain_path.write_text("cert chain")

    private_key_path = tmp_path / "pem"
    private_key_path.write_text("private key")

    mocker.patch(
        f"{MODULE}.input",
        side_effect=[
            "yes",
            str(private_key_path),
            str(chain_path),
        ],
    )
    stub = cfngin_context.add_stubber("iam")

    stub.add_client_error("get_server_certificate")
    stub.add_response(
        "upload_server_certificate",
        {
            "ServerCertificateMetadata": {
                "Path": "/",
                "ServerCertificateName": cert_name,
                "ServerCertificateId": "0" * 16,
                "Arn": arn,
                "UploadDate": datetime(2015, 1, 1),
                "Expiration": datetime(2015, 1, 1),
            }
        },
        {
            "ServerCertificateName": cert_name,
            "CertificateBody": certificate_path.read_text(),
            "PrivateKey": private_key_path.read_text(),
            "CertificateChain": chain_path.read_text(),
        },
    )

    with stub:
        assert ensure_server_cert_exists(
            cfngin_context,
            cert_name=cert_name,
            path_to_certificate=str(certificate_path),
        )
    stub.assert_no_pending_responses()


def test_ensure_server_cert_exists_already_exists(
    cfngin_context: MockCFNginContext,
) -> None:
    """Test ensure_server_cert_exists already exists."""
    cert_name = "foo"
    arn = f"arn:aws:iam::0123456789012:certification/{cert_name}"
    stub = cfngin_context.add_stubber("iam")

    stub.add_response(
        "get_server_certificate",
        {  # data required by botocore.stub
            "ServerCertificate": {
                "ServerCertificateMetadata": {
                    "Path": "/",
                    "ServerCertificateName": cert_name,
                    "ServerCertificateId": "0" * 16,
                    "Arn": arn,
                },
                "CertificateBody": "0",
            }
        },
        {"ServerCertificateName": cert_name},
    )

    with stub:
        assert ensure_server_cert_exists(cfngin_context, cert_name=cert_name) == {
            "cert_arn": arn,
            "cert_name": cert_name,
            "status": "exists",
        }
    stub.assert_no_pending_responses()


def test_ensure_server_cert_exists_no_prompt_no_parameters(
    cfngin_context: MockCFNginContext, mocker: MockerFixture
) -> None:
    """Test ensure_server_cert_exists no prompt, not parameters."""
    mocker.patch(
        f"{MODULE}.input",
        side_effect=["", "", ""],
    )
    stub = cfngin_context.add_stubber("iam")

    stub.add_client_error("get_server_certificate")

    with stub:
        assert not ensure_server_cert_exists(
            cfngin_context, cert_name="foo", prompt=False
        )
    stub.assert_no_pending_responses()


def test_ensure_server_cert_exists_prompt_no(
    cfngin_context: MockCFNginContext, mocker: MockerFixture
) -> None:
    """Test ensure_server_cert_exists prompt input no."""
    mocker.patch(
        f"{MODULE}.input",
        side_effect=["no"],
    )
    stub = cfngin_context.add_stubber("iam")

    stub.add_client_error("get_server_certificate")

    with stub:
        assert not ensure_server_cert_exists(cfngin_context, cert_name="foo")
    stub.assert_no_pending_responses()
