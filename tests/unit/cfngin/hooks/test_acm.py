"""Tests for runway.cfngin.hooks.acm."""

# pyright: reportUnknownArgumentType=none, reportUnknownVariableType=none
# pyright: reportUnknownLambdaType=none
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, NoReturn, cast
from unittest.mock import MagicMock

import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.stub import ANY, Stubber
from troposphere.certificatemanager import Certificate as CertificateResource

from runway.cfngin.exceptions import (
    StackDoesNotExist,
    StackFailed,
    StackUpdateBadStatus,
)
from runway.cfngin.hooks.acm import Certificate
from runway.cfngin.status import FAILED, NO_CHANGE, SubmittedStatus
from runway.utils import MutableMap

if TYPE_CHECKING:
    from mypy_boto3_acm.type_defs import DomainValidationTypeDef, ResourceRecordTypeDef
    from mypy_boto3_cloudformation.type_defs import StackResourceTypeDef
    from mypy_boto3_route53.type_defs import (
        ChangeInfoTypeDef,
        ChangeResourceRecordSetsResponseTypeDef,
        ChangeTypeDef,
        ResourceRecordSetTypeDef,
    )

    from ...factories import MockCfnginContext

STATUS = MutableMap(
    failed=FAILED,
    new=SubmittedStatus("creating new stack"),
    no=NO_CHANGE,
    recreate=SubmittedStatus("destroying stack for re-creation"),
    update=SubmittedStatus("updating existing stack"),
)


@pytest.fixture(autouse=True)
def sub_s3(cfngin_context: MockCfnginContext) -> None:
    """Sub s3 for MockCfnginContext as this hook uses a ``cached_property`` that creates it."""
    cfngin_context.add_stubber("s3")


def check_bool_is_true(val: Any) -> bool:
    """Check if a value is a true bool."""
    if val and isinstance(val, bool):
        return True
    raise ValueError(f'Value should be "True"; got {val}')


def check_bool_is_false(val: Any) -> bool:
    """Check if a value is a false bool."""
    if not val and isinstance(val, bool):
        return True
    raise ValueError(f'Value should be "False"; got {val}')


def gen_certificate(**kwargs: Any) -> dict[str, Any]:
    """Generate a response to describe_certificate."""
    data = {
        "CertificateArn": kwargs.pop("CertificateArn"),
        "DomainName": "place_holder_domain_name",
    }
    data.update(kwargs)
    return {"Certificate": data}


def gen_change(
    record_set: ResourceRecordSetTypeDef,
    action: Literal["CREATE", "DELETE", "UPSERT"] = "CREATE",
) -> ChangeTypeDef:
    """Generate expected change."""
    return {"Action": action, "ResourceRecordSet": record_set}


def gen_change_batch(changes: Any = ANY, comment: Any = ANY) -> dict[str, Any]:
    """Generate expected change batch."""
    return {"Comment": comment, "Changes": changes}


def gen_change_resource_record_sets(
    **kwargs: Any,
) -> ChangeResourceRecordSetsResponseTypeDef:
    """Generate response for change_resource_record_sets."""
    data: ChangeInfoTypeDef = {
        "Id": "placeholder_id",
        "Status": "PENDING",
        "SubmittedAt": datetime.now(),
        "Comment": "placeholder_comment",
    }
    data.update(kwargs)  # type: ignore
    return {"ChangeInfo": data}  # type: ignore


def gen_domain_validation_option(**kwargs: Any) -> DomainValidationTypeDef:
    """Generate a domain validation entry."""
    data: DomainValidationTypeDef = {
        "DomainName": "place_holder_domain_name",
        "ValidationStatus": "PENDING_VALIDATION",
        "ValidationDomain": "place_holder_validation_domain",
        "ResourceRecord": {
            "Name": "domain_name",
            "Type": "CNAME",
            "Value": "record_value",
        },
        "ValidationMethod": "DNS",
    }
    data.update(kwargs)  # type: ignore
    return data


def gen_record_set(
    use_resource_record: bool = False, **kwargs: Any
) -> ResourceRecordSetTypeDef | ResourceRecordTypeDef:
    """Generate a record set."""
    data: dict[str, Any] = {
        "Name": "placeholder_name",
        "Type": "CNAME",
        "Value": "placeholder_value",
    }
    if use_resource_record:
        data["ResourceRecords"] = kwargs.pop(
            "ResourceRecords", [{"Value": kwargs.pop("Value", data["Value"])}]
        )
        del data["Value"]

    data.update(kwargs)
    return data  # type: ignore


def gen_stack_resource(**kwargs: Any) -> StackResourceTypeDef:
    """Generate a response to describe_stack_resources."""
    data: StackResourceTypeDef = {
        "StackName": "place_holder_stack_name",
        "LogicalResourceId": "placeholder_logical_resource_id",
        "ResourceType": "placeholder_resource_type",
        "Timestamp": datetime.now(),
        "ResourceStatus": "CREATE_IN_PROGRESS",
    }
    data.update(kwargs)  # type: ignore
    return data


class TestCertificate:
    """Tests for runway.cfngin.hooks.acm.Certificate."""

    def test_attributes(self, cfngin_context: MockCfnginContext) -> None:
        """Test attributes set during __init__."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        result = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            alt_names=["example.net"],
            domain="example.com",
            hosted_zone_id="test",
            stack_name="stack-name",
            ttl=13,
        )

        assert result.stack_name == "stack-name"
        assert result.properties["DomainName"] == "example.com"
        assert result.properties["SubjectAlternativeNames"] == ["example.net"]
        # value tested in base class; just ensure its not None
        assert result.properties["Tags"]
        assert result.properties["ValidationMethod"] == "DNS"

        # blueprint attributes
        assert result.blueprint
        assert result.blueprint.VARIABLES["DomainName"]
        assert result.blueprint.VARIABLES["ValidateRecordTTL"]

        # template attributes
        template = result.blueprint.template
        assert template.description == result.get_template_description()
        assert not template.metadata
        assert not template.conditions
        assert not template.mappings
        assert template.outputs["DomainName"].Value.to_dict() == {"Ref": "DomainName"}
        assert template.outputs["ValidateRecordTTL"].Value.to_dict() == {"Ref": "ValidateRecordTTL"}
        assert not template.parameters
        assert isinstance(template.resources["Certificate"], CertificateResource)
        assert not template.rules
        assert template.version == "2010-09-09"
        assert not template.transform

        # stack attributes
        assert result.stack
        assert result.stack.fqn == "test-stack-name"
        assert result.stack.blueprint == result.blueprint  # type: ignore

    def test_domain_changed(self, cfngin_context: MockCfnginContext) -> None:
        """Test for domain_changed."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        provider = MagicMock()

        cert = Certificate(
            context=cfngin_context,
            provider=provider,
            domain="example.com",
            hosted_zone_id="test",
        )

        domain_match = {"DomainName": "example.com"}
        checks = [
            # is_stack_recreatable, is_stack_in_progress, is_stack_rolling_back, get_outputs
            (False, False, False, {"DomainName": "nope"}),
            (False, False, False, domain_match),
            (False, False, False, {}),
            (False, False, False, StackDoesNotExist("test")),
            (True, False, False, domain_match),
            (False, True, False, domain_match),
            (False, False, True, domain_match),
        ]

        provider.get_stack.return_value = True
        provider.is_stack_recreatable.side_effect = [x[0] for x in checks]
        provider.is_stack_in_progress.side_effect = [x[1] for x in checks]
        provider.is_stack_rolling_back.side_effect = [x[2] for x in checks]
        provider.get_outputs.side_effect = [x[3] for x in checks]

        # output based
        assert cert.domain_changed()  # {'DomainName': 'nope'}
        assert not cert.domain_changed()  # {'DomainName': 'example.com'}
        assert not cert.domain_changed()  # {}
        assert not cert.domain_changed()  # StackDoesNotExist('test')
        # status based
        assert not cert.domain_changed()
        assert not cert.domain_changed()
        assert not cert.domain_changed()

    def test_get_certificate(
        self, cfngin_context: MockCfnginContext, mock_sleep: None  # noqa: ARG002
    ) -> None:
        """Test get_certificate."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        provider = MagicMock(cloudformation=boto3.client("cloudformation"))
        cfn_stubber = Stubber(provider.cloudformation)

        cert = Certificate(
            context=cfngin_context,
            provider=provider,
            domain="example.com",
            hosted_zone_id="test",
        )

        expected_request = {
            "StackName": "test-example-com",
            "LogicalResourceId": "Certificate",
        }

        cfn_stubber.add_response(
            "describe_stack_resources", {"StackResources": []}, expected_request
        )
        cfn_stubber.add_response(
            "describe_stack_resources",
            {"StackResources": [gen_stack_resource()]},
            expected_request,
        )
        cfn_stubber.add_response(
            "describe_stack_resources",
            {"StackResources": [gen_stack_resource(PhysicalResourceId="success")]},
            expected_request,
        )

        with cfn_stubber:
            assert cert.get_certificate() == "success"

        cfn_stubber.assert_no_pending_responses()

    @pytest.mark.parametrize("status", ["PENDING_VALIDATION", "SUCCESS", "FAILED"])
    def test_get_validation_record(
        self,
        cfngin_context: MockCfnginContext,
        monkeypatch: pytest.MonkeyPatch,
        mock_sleep: None,  # noqa: ARG002
        status: str,
    ) -> None:
        """Test get_validation_record."""
        # setup context
        acm_stubber = cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert_arn = "arn:aws:acm:us-east-1:012345678901:certificate/test"
        expected_request = {"CertificateArn": cert_arn}
        validate_option_missing_record = gen_domain_validation_option(ValidationStatus=status)
        del validate_option_missing_record["ResourceRecord"]

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        monkeypatch.setattr(cert, "get_certificate", lambda: cert_arn)

        acm_stubber.add_response(
            "describe_certificate",
            gen_certificate(CertificateArn=cert_arn),
            expected_request,
        )
        acm_stubber.add_response(
            "describe_certificate",
            gen_certificate(
                CertificateArn=cert_arn,
                DomainValidationOptions=[validate_option_missing_record],
            ),
            expected_request,
        )
        acm_stubber.add_response(
            "describe_certificate",
            gen_certificate(
                CertificateArn=cert_arn,
                DomainValidationOptions=[gen_domain_validation_option(ValidationStatus=status)],
            ),
            expected_request,
        )

        with acm_stubber:
            assert cert.get_validation_record(status=status) == gen_domain_validation_option().get(
                "ResourceRecord"
            )
        acm_stubber.assert_no_pending_responses()

    @pytest.mark.parametrize(
        "check,found",
        [
            ("PENDING_VALIDATION", "SUCCESS"),
            ("SUCCESS", "PENDING_VALIDATION"),
            ("FAILED", "SUCCESS"),
        ],
    )
    def test_get_validation_record_status_missmatch(
        self, cfngin_context: MockCfnginContext, check: str, found: str
    ) -> None:
        """Test get get_validation_record with a missmatched record status."""
        # setup context
        acm_stubber = cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert_arn = "arn:aws:acm:us-east-1:012345678901:certificate/test"
        expected_request = {"CertificateArn": cert_arn}

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )

        acm_stubber.add_response(
            "describe_certificate",
            gen_certificate(
                CertificateArn=cert_arn,
                DomainValidationOptions=[gen_domain_validation_option(ValidationStatus=found)],
            ),
            expected_request,
        )

        with acm_stubber, pytest.raises(ValueError, match="No validations with status"):
            cert.get_validation_record(cert_arn=cert_arn, status=check)
        acm_stubber.assert_no_pending_responses()

    def test_get_validation_record_gt_one(self, cfngin_context: MockCfnginContext) -> None:
        """Test get get_validation_record more than one result."""
        # setup context
        acm_stubber = cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert_arn = "arn:aws:acm:us-east-1:012345678901:certificate/test"
        expected_request = {"CertificateArn": cert_arn}

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )

        acm_stubber.add_response(
            "describe_certificate",
            gen_certificate(
                CertificateArn=cert_arn,
                DomainValidationOptions=[
                    gen_domain_validation_option(),
                    gen_domain_validation_option(),
                ],
            ),
            expected_request,
        )

        with (
            acm_stubber,
            pytest.raises(ValueError, match="only one option is supported"),
        ):
            cert.get_validation_record(cert_arn=cert_arn)
        acm_stubber.assert_no_pending_responses()

    def test_put_record_set(self, cfngin_context: MockCfnginContext) -> None:
        """Test put_record."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        r53_stubber = cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )

        r53_stubber.add_response(
            "change_resource_record_sets",
            gen_change_resource_record_sets(),
            {
                "HostedZoneId": cert.args.hosted_zone_id,
                "ChangeBatch": gen_change_batch(
                    changes=[
                        gen_change(
                            record_set=cast(
                                "ResourceRecordSetTypeDef",
                                gen_record_set(use_resource_record=True, TTL=cert.args.ttl),
                            )
                        )
                    ]
                ),
            },
        )

        with r53_stubber:
            assert not cert.put_record_set(cast("ResourceRecordTypeDef", gen_record_set()))
        r53_stubber.assert_no_pending_responses()

    def test_remove_validation_records(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test remove_validation_records."""
        # setup context
        acm_stubber = cfngin_context.add_stubber("acm", region="us-east-1")
        r53_stubber = cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert_arn = "arn:aws:acm:us-east-1:012345678901:certificate/test"
        expected_cert_request = {"CertificateArn": cert_arn}

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        monkeypatch.setattr(cert, "get_certificate", lambda: cert_arn)

        acm_stubber.add_response(
            "describe_certificate",
            gen_certificate(
                CertificateArn=cert_arn,
                DomainValidationOptions=[gen_domain_validation_option()],
            ),
            expected_cert_request,
        )
        acm_stubber.add_response(
            "describe_certificate",
            gen_certificate(
                CertificateArn=cert_arn,
                DomainValidationOptions=[gen_domain_validation_option(ValidationMethod="EMAIL")],
            ),
            expected_cert_request,
        )

        r53_stubber.add_response(
            "change_resource_record_sets",
            gen_change_resource_record_sets(),
            {
                "HostedZoneId": cert.args.hosted_zone_id,
                "ChangeBatch": gen_change_batch(
                    changes=[
                        gen_change(
                            action="DELETE",
                            record_set=cast(
                                "ResourceRecordSetTypeDef",
                                gen_record_set(
                                    use_resource_record=True,
                                    TTL=cert.args.ttl,
                                    **gen_domain_validation_option().get("ResourceRecord", {}),
                                ),
                            ),
                        )
                    ]
                ),
            },
        )

        with (  # noqa: PT012
            acm_stubber,
            r53_stubber,
            pytest.raises(ValueError, match="Must provide one of more record sets"),
        ):
            assert not cert.remove_validation_records()
            cert.remove_validation_records()

        acm_stubber.assert_no_pending_responses()
        r53_stubber.assert_no_pending_responses()

    def test_update_record_set(self, cfngin_context: MockCfnginContext) -> None:
        """Test update_record_set."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        r53_stubber = cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )

        r53_stubber.add_response(
            "change_resource_record_sets",
            gen_change_resource_record_sets(),
            {
                "HostedZoneId": cert.args.hosted_zone_id,
                "ChangeBatch": gen_change_batch(
                    changes=[
                        gen_change(
                            action="UPSERT",
                            record_set=cast(
                                "ResourceRecordSetTypeDef",
                                gen_record_set(use_resource_record=True, TTL=cert.args.ttl),
                            ),
                        )
                    ]
                ),
            },
        )

        with r53_stubber:
            assert not cert.update_record_set(cast("ResourceRecordTypeDef", gen_record_set()))
        r53_stubber.assert_no_pending_responses()

    def test_deploy(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test deploy."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert_arn = "arn:aws:acm:us-east-1:012345678901:certificate/test"
        expected = {"CertificateArn": cert_arn}

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        monkeypatch.setattr(cert, "domain_changed", lambda: False)
        monkeypatch.setattr(cert, "deploy_stack", lambda: STATUS.new)  # type: ignore
        monkeypatch.setattr(cert, "get_certificate", lambda: cert_arn)
        monkeypatch.setattr(
            cert,
            "get_validation_record",
            lambda x: "get_validation_record" if x == cert_arn else ValueError,
        )
        monkeypatch.setattr(
            cert,
            "put_record_set",
            lambda x: None if x == "get_validation_record" else ValueError,
        )
        monkeypatch.setattr(cert, "_wait_for_stack", lambda _, last_status: None)  # noqa: ARG005

        assert cert.deploy() == expected

    def test_deploy_update(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test deploy update stack."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert_arn = "arn:aws:acm:us-east-1:012345678901:certificate/test"
        expected = {"CertificateArn": cert_arn}

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        monkeypatch.setattr(cert, "domain_changed", lambda: False)
        monkeypatch.setattr(cert, "deploy_stack", lambda: STATUS.update)
        monkeypatch.setattr(cert, "get_certificate", lambda: cert_arn)
        monkeypatch.setattr(
            cert,
            "get_validation_record",
            lambda x, status: (
                "get_validation_record" if x == cert_arn and status == "SUCCESS" else ValueError
            ),
        )
        monkeypatch.setattr(
            cert,
            "update_record_set",
            lambda x: None if x == "get_validation_record" else ValueError,
        )
        monkeypatch.setattr(cert, "_wait_for_stack", lambda _, last_status: None)  # noqa: ARG005

        assert cert.deploy() == expected

    def test_deploy_no_change(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test deploy no change."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert_arn = "arn:aws:acm:us-east-1:012345678901:certificate/test"
        expected = {"CertificateArn": cert_arn}

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        monkeypatch.setattr(cert, "domain_changed", lambda: False)
        monkeypatch.setattr(cert, "deploy_stack", lambda: STATUS.no)  # type: ignore
        monkeypatch.setattr(cert, "get_certificate", lambda: cert_arn)

        assert cert.deploy() == expected

    def test_deploy_recreate(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test deploy with stack recreation."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert_arn = "arn:aws:acm:us-east-1:012345678901:certificate/test"
        expected = {"CertificateArn": cert_arn}

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        monkeypatch.setattr(cert, "domain_changed", lambda: False)
        monkeypatch.setattr(cert, "deploy_stack", lambda: STATUS.recreate)  # type: ignore
        monkeypatch.setattr(cert, "get_certificate", MagicMock(side_effect=["old", cert_arn]))
        monkeypatch.setattr(
            cert, "_wait_for_stack", MagicMock(side_effect=[STATUS.new, None])  # type: ignore
        )
        monkeypatch.setattr(
            cert,
            "get_validation_record",
            lambda x: "get_validation_record" if x == cert_arn else ValueError,
        )
        monkeypatch.setattr(
            cert,
            "put_record_set",
            lambda x: None if x == "get_validation_record" else ValueError,
        )

        assert cert.deploy() == expected

    def test_deploy_domain_changed(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test deploy domain changed."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        monkeypatch.setattr(cert, "domain_changed", lambda: True)

        assert not cert.deploy()

    def test_deploy_error_destroy(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test deploy with errors that result in destroy being called."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert_arn = "arn:aws:acm:us-east-1:012345678901:certificate/test"

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )

        monkeypatch.setattr(cert, "domain_changed", lambda: False)
        monkeypatch.setattr(cert, "deploy_stack", lambda: STATUS.new)  # type: ignore
        monkeypatch.setattr(cert, "get_certificate", lambda: cert_arn)
        monkeypatch.setattr(
            cert,
            "get_validation_record",
            lambda x: "get_validation_record" if x == cert_arn else ValueError,
        )
        monkeypatch.setattr(
            cert,
            "put_record_set",
            MagicMock(
                side_effect=[
                    cert.r53_client.exceptions.InvalidChangeBatch({}, ""),
                    cert.r53_client.exceptions.NoSuchHostedZone({}, ""),
                    None,
                ]
            ),
        )
        monkeypatch.setattr(
            cert,
            "destroy",
            lambda records, skip_r53: check_bool_is_true(skip_r53),  # noqa: ARG005
        )
        monkeypatch.setattr(cert, "_wait_for_stack", MagicMock(side_effect=StackFailed("test")))

        assert not cert.deploy()  # cert.r53_client.exceptions.InvalidChangeBatch
        assert not cert.deploy()  # cert.r53_client.exceptions.NoSuchHostedZone

        monkeypatch.setattr(
            cert,
            "destroy",
            lambda records, skip_r53: check_bool_is_false(skip_r53),  # noqa: ARG005
        )
        assert not cert.deploy()  # StackFailed

    def test_deploy_error_no_destroy(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test deploy with errors that don't result in destroy being called."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        monkeypatch.setattr(cert, "domain_changed", lambda: False)
        monkeypatch.setattr(
            cert,
            "deploy_stack",
            MagicMock(side_effect=StackUpdateBadStatus("test", "test", "test")),
        )

        assert not cert.deploy()

    def test_destroy(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test destroy."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        # should only be called once
        monkeypatch.setattr(cert, "remove_validation_records", MagicMock(return_value=None))
        monkeypatch.setattr(cert, "destroy_stack", lambda wait: None)  # noqa: ARG005

        assert cert.destroy()
        assert cert.destroy(skip_r53=True)
        assert cert.remove_validation_records.call_count == 1  # type: ignore

    def test_destroy_aws_errors(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test destroy with errors from AWS."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )

        monkeypatch.setattr(
            cert,
            "remove_validation_records",
            MagicMock(
                side_effect=[
                    cert.r53_client.exceptions.InvalidChangeBatch({}, ""),
                    cert.r53_client.exceptions.NoSuchHostedZone({}, ""),
                    cert.acm_client.exceptions.ResourceNotFoundException({}, ""),
                ]
            ),
        )
        monkeypatch.setattr(cert, "destroy_stack", lambda wait: None)  # noqa: ARG005

        assert cert.destroy()
        assert cert.destroy()
        assert cert.destroy()

    def test_destroy_raise_client_error(
        self, cfngin_context: MockCfnginContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test destroy with ClientError raised."""
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        def build_client_error(msg: str) -> ClientError:
            """Raise a ClientError."""
            return ClientError({"Error": {"Code": "", "Message": msg}}, "test")

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        monkeypatch.setattr(cert, "destroy_stack", lambda wait: None)  # noqa: ARG005

        def raise_stack_not_exist(_records: Any) -> NoReturn:
            """Raise ClientError mimicking stack not existing."""
            assert cert.stack
            raise build_client_error(f"Stack with id {cert.stack.fqn} does not exist")

        def raise_other(_records: Any) -> NoReturn:
            """Raise other ClientError."""
            raise build_client_error("something")

        monkeypatch.setattr(cert, "remove_validation_records", raise_stack_not_exist)
        assert cert.destroy()

        monkeypatch.setattr(cert, "remove_validation_records", raise_other)
        with pytest.raises(ClientError) as excinfo:
            cert.destroy()
        assert "something" in str(excinfo.value)

    @pytest.mark.parametrize(
        "stage,expected",
        [
            ("post_deploy", "deploy"),
            ("post_destroy", "destroy"),
            ("pre_deploy", "deploy"),
            ("pre_destroy", "destroy"),
        ],
    )
    def test_stage_methods(
        self,
        cfngin_context: MockCfnginContext,
        monkeypatch: pytest.MonkeyPatch,
        stage: str,
        expected: str,
    ) -> None:
        """Test stage methods.

        All of these call a different method that is being tested separately
        so this test just ensures each stage is mapped to the correct method
        on the backend.

        """
        # setup context
        cfngin_context.add_stubber("acm", region="us-east-1")
        cfngin_context.add_stubber("route53", region="us-east-1")
        cfngin_context.config.namespace = "test"

        cert = Certificate(
            context=cfngin_context,
            provider=MagicMock(),
            domain="example.com",
            hosted_zone_id="test",
        )
        monkeypatch.setattr(cert, "deploy", lambda: "deploy")
        monkeypatch.setattr(cert, "destroy", lambda: "destroy")

        assert getattr(cert, stage)() == expected
