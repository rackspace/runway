"""Test runway.cfngin.hooks.ssm.parameter."""
# pylint: disable=no-self-use
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from botocore.exceptions import ClientError
from pydantic import ValidationError

from runway._logging import LogLevels
from runway.cfngin.hooks.ssm.parameter import ArgsDataModel, SecureString
from runway.cfngin.hooks.ssm.parameter import _Parameter as Parameter
from runway.cfngin.hooks.utils import TagDataModel

if TYPE_CHECKING:
    from botocore.stub import Stubber
    from mypy_boto3_ssm.client import SSMClient
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture

    from runway.context import CfnginContext

MODULE = "runway.cfngin.hooks.ssm.parameter"


class TestArgsDataModel:
    """Test ArgsDataModel."""

    def test_field_defaults(self) -> None:
        """Test field values."""
        obj = ArgsDataModel(name="test", type="String")
        assert not obj.allowed_pattern
        assert not obj.data_type
        assert not obj.description
        assert obj.force is False
        assert not obj.key_id
        assert obj.name == "test"
        assert obj.overwrite is True
        assert not obj.policies
        assert not obj.tags
        assert obj.tier == "Standard"
        assert obj.type == "String"
        assert not obj.value

    def test_name_required(self) -> None:
        """Test name."""
        with pytest.raises(ValidationError, match="Name\n  field required"):
            ArgsDataModel.parse_obj({"type": "String"})

    def test_policies_raise_type_error(self) -> None:
        """Test policies."""
        with pytest.raises(ValidationError, match="Policies"):
            assert not ArgsDataModel(
                name="test",
                Policies=True,  # type: ignore
                type="String",
            )

    def test_policies_json(self) -> None:
        """Test policies."""
        data = [
            {
                "Type": "Expiration",
                "Version": "1.0",
                "Attributes": {"Timestamp": "2018-12-02T21:34:33.000Z"},
            }
        ]
        assert ArgsDataModel(
            name="test",
            Policies=data,  # type: ignore
            type="String",
        ).policies == json.dumps(data)

    def test_policies_string(self) -> None:
        """Test policies."""
        data = json.dumps(
            [
                {
                    "Type": "Expiration",
                    "Version": "1.0",
                    "Attributes": {"Timestamp": "2018-12-02T21:34:33.000Z"},
                }
            ]
        )
        assert ArgsDataModel(name="test", policies=data, type="String").policies == data

    def test_tags_dict(self) -> None:
        """Test tags."""
        assert ArgsDataModel(
            name="test",
            tags={"tag-key": "tag-value"},  # type: ignore
            type="String",
        ).tags == [TagDataModel(key="tag-key", value="tag-value")]

    def test_tags_raise_type_error(self) -> None:
        """Test tags."""
        with pytest.raises(ValidationError, match="Tags"):
            assert not ArgsDataModel.parse_obj(
                {"name": "test", "tags": "", "type": "String"}
            )

    def test_tier_invalid(self) -> None:
        """Test tier."""
        with pytest.raises(ValidationError, match="Tier\n  unexpected value"):
            ArgsDataModel.parse_obj(
                {"name": "test", "tier": "invalid", "type": "String"}
            )

    def test_type_invalid(self) -> None:
        """Test name."""
        with pytest.raises(ValidationError, match="Type\n  unexpected value"):
            ArgsDataModel.parse_obj({"name": "test", "type": "invalid"})

    def test_type_required(self) -> None:
        """Test name."""
        with pytest.raises(ValidationError, match="Type\n  field required"):
            ArgsDataModel.parse_obj({"name": "test"})


class TestParameter:
    """Test Parameter."""

    def test___init__(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test __init__."""
        args = mocker.patch(f"{MODULE}.ArgsDataModel")
        args.parse_obj.return_value = args
        data = {"key": "val"}
        obj = Parameter(cfngin_context, name="test", type="String", **data)
        assert obj.args == args
        assert obj.ctx == cfngin_context
        args.parse_obj.assert_called_once_with(
            {"name": "test", "type": "String", **data}
        )

    def test_client(
        self,
        cfngin_context: CfnginContext,
        mocker: MockerFixture,
        ssm_client: SSMClient,
    ) -> None:
        """Test client."""
        mocker.patch(f"{MODULE}.ArgsDataModel")
        assert (
            Parameter(cfngin_context, name="test", type="String").client == ssm_client
        )

    def test_delete(
        self,
        caplog: LogCaptureFixture,
        cfngin_context: CfnginContext,
        ssm_stubber: Stubber,
    ) -> None:
        """Test delete."""
        caplog.set_level(LogLevels.INFO, logger=MODULE)
        ssm_stubber.add_response("delete_parameter", {}, {"Name": "test"})
        with ssm_stubber:
            assert Parameter(cfngin_context, name="test", type="String").delete()
        ssm_stubber.assert_no_pending_responses()
        assert "deleted SSM Parameter test" in caplog.messages

    def test_delete_handle_parameter_not_found(
        self,
        caplog: LogCaptureFixture,
        cfngin_context: CfnginContext,
        ssm_stubber: Stubber,
    ) -> None:
        """Test delete."""
        caplog.set_level(LogLevels.INFO, logger=MODULE)
        ssm_stubber.add_client_error("delete_parameter", "ParameterNotFound")
        with ssm_stubber:
            assert Parameter(cfngin_context, name="test", type="String").delete()
        ssm_stubber.assert_no_pending_responses()
        assert "delete parameter skipped; test not found" in caplog.messages

    def test_delete_raise_client_error(
        self,
        cfngin_context: CfnginContext,
        ssm_stubber: Stubber,
    ) -> None:
        """Test delete."""
        ssm_stubber.add_client_error("delete_parameter")
        with ssm_stubber, pytest.raises(ClientError):
            assert not Parameter(cfngin_context, name="test", type="String").delete()
        ssm_stubber.assert_no_pending_responses()

    def test_get(
        self,
        cfngin_context: CfnginContext,
        ssm_stubber: Stubber,
    ) -> None:
        """Test get."""
        data = {
            "Name": "test",
            "Type": "String",
            "Value": "test",
            "Version": 1,
        }
        ssm_stubber.add_response(
            "get_parameter",
            {"Parameter": data},
            {"Name": "test", "WithDecryption": True},
        )
        with ssm_stubber:
            assert Parameter(cfngin_context, name="test", type="String").get() == data
        ssm_stubber.assert_no_pending_responses()

    def test_get_force(
        self,
        cfngin_context: CfnginContext,
        ssm_stubber: Stubber,
    ) -> None:
        """Test get."""
        ssm_stubber.add_response(
            "get_parameter",
            {
                "Parameter": {
                    "Name": "test",
                    "Type": "String",
                    "Value": "test",
                    "Version": 1,
                }
            },
        )
        with ssm_stubber:
            assert (
                Parameter(cfngin_context, force=True, name="test", type="String").get()
                == {}
            )

    def test_get_handle_parameter_not_found(
        self,
        caplog: LogCaptureFixture,
        cfngin_context: CfnginContext,
        ssm_stubber: Stubber,
    ) -> None:
        """Test get."""
        caplog.set_level(LogLevels.VERBOSE, logger=MODULE)
        ssm_stubber.add_client_error("get_parameter", "ParameterNotFound")
        with ssm_stubber:
            assert Parameter(cfngin_context, name="test", type="String").get() == {}
        ssm_stubber.assert_no_pending_responses()
        assert "parameter test does not exist" in caplog.messages

    def test_get_raise_client_error(
        self,
        cfngin_context: CfnginContext,
        ssm_stubber: Stubber,
    ) -> None:
        """Test get."""
        ssm_stubber.add_client_error("get_parameter")
        with ssm_stubber, pytest.raises(ClientError):
            assert not Parameter(cfngin_context, name="test", type="String").get()
        ssm_stubber.assert_no_pending_responses()

    def test_get_current_tags(
        self, cfngin_context: CfnginContext, ssm_stubber: Stubber
    ) -> None:
        """Test get_current_tags."""
        data = [{"Key": "test-key", "Value": "test-val"}]
        ssm_stubber.add_response(
            "list_tags_for_resource",
            {"TagList": data},
            {"ResourceId": "test", "ResourceType": "Parameter"},
        )
        with ssm_stubber:
            assert (
                Parameter(cfngin_context, name="test", type="String").get_current_tags()
                == data
            )
        ssm_stubber.assert_no_pending_responses()

    def test_get_current_tags_empty(
        self, cfngin_context: CfnginContext, ssm_stubber: Stubber
    ) -> None:
        """Test get_current_tags."""
        ssm_stubber.add_response("list_tags_for_resource", {})
        with ssm_stubber:
            assert (
                Parameter(cfngin_context, name="test", type="String").get_current_tags()
                == []
            )
        ssm_stubber.assert_no_pending_responses()

    def test_get_current_tags_handle_invalid_resource_id(
        self, cfngin_context: CfnginContext, ssm_stubber: Stubber
    ) -> None:
        """Test get_current_tags."""
        ssm_stubber.add_client_error("list_tags_for_resource", "InvalidResourceId")
        with ssm_stubber:
            assert (
                Parameter(cfngin_context, name="test", type="String").get_current_tags()
                == []
            )
        ssm_stubber.assert_no_pending_responses()

    def test_get_current_tags_handle_parameter_not_found(
        self, cfngin_context: CfnginContext, ssm_stubber: Stubber
    ) -> None:
        """Test get_current_tags."""
        ssm_stubber.add_client_error("list_tags_for_resource", "ParameterNotFound")
        with ssm_stubber:
            assert (
                Parameter(cfngin_context, name="test", type="String").get_current_tags()
                == []
            )
        ssm_stubber.assert_no_pending_responses()

    def test_get_current_tags_raise_client_error(
        self, cfngin_context: CfnginContext, ssm_stubber: Stubber
    ) -> None:
        """Test get_current_tags."""
        ssm_stubber.add_client_error("list_tags_for_resource")
        with ssm_stubber, pytest.raises(ClientError):
            assert Parameter(
                cfngin_context, name="test", type="String"
            ).get_current_tags()
        ssm_stubber.assert_no_pending_responses()

    def test_post_deploy(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test post_deploy."""
        mock_put = mocker.patch.object(Parameter, "put", return_value="success")
        mock_update_tags = mocker.patch.object(
            Parameter, "update_tags", return_value=None
        )
        assert (
            Parameter(cfngin_context, name="test", type="String").post_deploy()
            == mock_put.return_value
        )
        mock_put.assert_called_once_with()
        mock_update_tags.assert_called_once_with()

    def test_post_destroy(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test post_destroy."""
        mock_delete = mocker.patch.object(Parameter, "delete", return_value="success")
        assert (
            Parameter(cfngin_context, name="test", type="String").post_destroy()
            == mock_delete.return_value
        )
        mock_delete.assert_called_once_with()

    def test_pre_deploy(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test pre_deploy."""
        mock_put = mocker.patch.object(Parameter, "put", return_value="success")
        mock_update_tags = mocker.patch.object(
            Parameter, "update_tags", return_value=None
        )
        assert (
            Parameter(cfngin_context, name="test", type="String").pre_deploy()
            == mock_put.return_value
        )
        mock_put.assert_called_once_with()
        mock_update_tags.assert_called_once_with()

    def test_pre_destroy(
        self, cfngin_context: CfnginContext, mocker: MockerFixture
    ) -> None:
        """Test pre_destroy."""
        mock_delete = mocker.patch.object(Parameter, "delete", return_value="success")
        assert (
            Parameter(cfngin_context, name="test", type="String").pre_destroy()
            == mock_delete.return_value
        )
        mock_delete.assert_called_once_with()

    def test_put(
        self,
        caplog: LogCaptureFixture,
        cfngin_context: CfnginContext,
        mocker: MockerFixture,
        ssm_stubber: Stubber,
    ) -> None:
        """Test put."""
        caplog.set_level(LogLevels.INFO, MODULE)
        expected = {"Tier": "Standard", "Version": 1}
        mock_get = mocker.patch.object(Parameter, "get", return_value={})
        ssm_stubber.add_response(
            "put_parameter",
            expected,
            {
                "Name": "test",
                "Overwrite": True,
                "Tier": "Standard",
                "Type": "String",
                "Value": "foo",
            },
        )
        with ssm_stubber:
            assert (
                Parameter(
                    cfngin_context,
                    name="test",
                    tags=[{"Key": "k", "Value": "v"}],
                    type="String",
                    value="foo",
                ).put()
                == expected
            )
        mock_get.assert_called_once_with()
        ssm_stubber.assert_no_pending_responses()
        assert "put SSM Parameter test" in caplog.messages

    def test_put_handle_parameter_already_exists(
        self,
        caplog: LogCaptureFixture,
        cfngin_context: CfnginContext,
        mocker: MockerFixture,
        ssm_stubber: Stubber,
    ) -> None:
        """Test put."""
        caplog.set_level(LogLevels.WARNING, MODULE)
        expected = {"Tier": "Standard", "Version": 1}
        mocker.patch.object(Parameter, "get", return_value=expected)
        ssm_stubber.add_client_error("put_parameter", "ParameterAlreadyExists")
        with ssm_stubber:
            assert (
                Parameter(cfngin_context, name="test", type="String", value="foo").put()
                == expected
            )
        assert (
            "parameter test already exists; to overwrite it's value, "
            'set the overwrite field to "true"' in caplog.messages
        )

    def test_put_no_value(
        self,
        caplog: LogCaptureFixture,
        cfngin_context: CfnginContext,
    ) -> None:
        """Test put."""
        caplog.set_level(LogLevels.INFO, MODULE)
        assert Parameter(
            cfngin_context, name="test", type="String", value=None
        ).put() == {"Tier": "Standard", "Version": 0}
        assert (
            "skipped putting SSM Parameter; value provided for test is falsy"
            in caplog.messages
        )

    def test_put_raise_client_error(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, ssm_stubber: Stubber
    ) -> None:
        """Test put."""
        mocker.patch.object(
            Parameter,
            "get",
            return_value={},
        )
        ssm_stubber.add_client_error("put_parameter")
        with ssm_stubber, pytest.raises(ClientError):
            assert not Parameter(
                cfngin_context, name="test", type="String", value="foo"
            ).put()

    def test_put_same_value(
        self,
        cfngin_context: CfnginContext,
        mocker: MockerFixture,
    ) -> None:
        """Test put."""
        expected = {"Tier": "Advanced", "Version": 10}
        mock_get = mocker.patch.object(
            Parameter,
            "get",
            return_value={"Value": "foo", **expected},
        )
        assert (
            Parameter(cfngin_context, name="test", type="String", value="foo").put()
            == expected
        )
        mock_get.assert_called_once_with()

    def test_update_tags(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, ssm_stubber: Stubber
    ) -> None:
        """Test update_tags."""
        current_tags = [
            {"Key": "current", "Value": "current-value"},
            {"Key": "retain", "Value": "retain"},
        ]
        new_tags = [
            {"Key": "new", "Value": "new-value"},
            {"Key": "retain", "Value": "retain"},
        ]
        get_current_tags = mocker.patch.object(
            Parameter, "get_current_tags", return_value=current_tags
        )
        ssm_stubber.add_response(
            "remove_tags_from_resource",
            {},
            {
                "ResourceId": "test",
                "ResourceType": "Parameter",
                "TagKeys": ["current", "new"],
            },
        )
        ssm_stubber.add_response(
            "add_tags_to_resource",
            {},
            {"ResourceId": "test", "ResourceType": "Parameter", "Tags": new_tags},
        )
        with ssm_stubber:
            assert not Parameter(
                cfngin_context, name="test", tags=new_tags, type="String"
            ).update_tags()
        get_current_tags.assert_called_once_with()
        ssm_stubber.assert_no_pending_responses()

    def test_update_tags_add_only(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, ssm_stubber: Stubber
    ) -> None:
        """Test update_tags."""
        new_tags = [
            {"Key": "new", "Value": "new-value"},
            {"Key": "retain", "Value": "retain"},
        ]
        mocker.patch.object(Parameter, "get_current_tags", return_value=[])
        ssm_stubber.add_response(
            "add_tags_to_resource",
            {},
            {"ResourceId": "test", "ResourceType": "Parameter", "Tags": new_tags},
        )
        with ssm_stubber:
            assert not Parameter(
                cfngin_context, name="test", tags=new_tags, type="String"
            ).update_tags()

    def test_update_tags_add_only_raise_client_error(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, ssm_stubber: Stubber
    ) -> None:
        """Test update_tags raise ClientError."""
        new_tags = [
            {"Key": "new", "Value": "new-value"},
            {"Key": "retain", "Value": "retain"},
        ]
        mocker.patch.object(Parameter, "get_current_tags", return_value=[])
        ssm_stubber.add_client_error("add_tags_to_resource")
        with ssm_stubber, pytest.raises(ClientError):
            assert Parameter(
                cfngin_context, name="test", tags=new_tags, type="String"
            ).update_tags()
        ssm_stubber.assert_no_pending_responses()

    def test_update_tags_delete_only(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, ssm_stubber: Stubber
    ) -> None:
        """Test update_tags."""
        current_tags = [
            {"Key": "current", "Value": "current-value"},
            {"Key": "retain", "Value": "retain"},
        ]
        mocker.patch.object(Parameter, "get_current_tags", return_value=current_tags)
        ssm_stubber.add_response(
            "remove_tags_from_resource",
            {},
            {
                "ResourceId": "test",
                "ResourceType": "Parameter",
                "TagKeys": ["current", "retain"],
            },
        )
        ssm_stubber.add_client_error("add_tags_to_resource")
        with ssm_stubber:
            assert not Parameter(
                cfngin_context, name="test", type="String"
            ).update_tags()

    def test_update_tags_delete_only_raise_client_error(
        self, cfngin_context: CfnginContext, mocker: MockerFixture, ssm_stubber: Stubber
    ) -> None:
        """Test update_tags raise ClientError."""
        current_tags = [
            {"Key": "new", "Value": "current-value"},
            {"Key": "retain", "Value": "retain"},
        ]
        mocker.patch.object(Parameter, "get_current_tags", return_value=current_tags)
        ssm_stubber.add_client_error("remove_tags_from_resource")
        with ssm_stubber, pytest.raises(ClientError):
            assert Parameter(cfngin_context, name="test", type="String").update_tags()
        ssm_stubber.assert_no_pending_responses()

    def test_update_tags_handle_invalid_resource_id(
        self,
        caplog: LogCaptureFixture,
        cfngin_context: CfnginContext,
        mocker: MockerFixture,
        ssm_stubber: Stubber,
    ) -> None:
        """Test update_tags handle InvalidResourceId. Can only happen during add."""
        caplog.set_level(LogLevels.INFO, logger=MODULE)
        new_tags = [
            {"Key": "new", "Value": "new-value"},
            {"Key": "retain", "Value": "retain"},
        ]
        mocker.patch.object(Parameter, "get_current_tags", return_value=[])
        ssm_stubber.add_client_error("add_tags_to_resource", "InvalidResourceId")
        with ssm_stubber:
            assert not Parameter(
                cfngin_context, name="test", tags=new_tags, type="String"
            ).update_tags()
        ssm_stubber.assert_no_pending_responses()
        assert "skipped updating tags; parameter test does not exist" in caplog.messages
        assert "updated tags for parameter test" not in caplog.messages


class TestSecureString:
    """Test SecureString."""

    def test___init__(self, cfngin_context: CfnginContext) -> None:
        """Test __init__."""
        obj = SecureString(cfngin_context, name="test")
        assert obj.ctx == cfngin_context
        assert obj.args.name == "test"
        assert obj.args.type == "SecureString"
