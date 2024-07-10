"""Test runway.context._cfngin."""

# pyright: basic
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union, cast

import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber
from mock import MagicMock

from runway.cfngin.exceptions import (
    PersistentGraphCannotLock,
    PersistentGraphCannotUnlock,
    PersistentGraphLockCodeMismatch,
    PersistentGraphLocked,
    PersistentGraphUnlocked,
)
from runway.cfngin.plan import Graph, json_serial
from runway.cfngin.stack import Stack
from runway.config import CfnginConfig
from runway.context._cfngin import CfnginContext, get_fqn
from runway.core.components import DeployEnvironment

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.core.providers.aws.type_defs import TagSetTypeDef
    from runway.type_defs import Boto3CredentialsTypeDef

MODULE = "runway.context._cfngin"

BOTO3_CREDENTIALS: Boto3CredentialsTypeDef = {
    "aws_access_key_id": "foo",
    "aws_secret_access_key": "bar",
    "aws_session_token": "foobar",
}


def gen_tagset(tags: Dict[str, str]) -> TagSetTypeDef:
    """Create TagSet value from a dict."""
    return [{"Key": key, "Value": value} for key, value in tags.items()]


def gen_s3_object_content(content: Union[Dict[str, Any], str]) -> StreamingBody:
    """Convert a string or dict to S3 object body.

    Args:
        content: S3 object body.

    """
    if isinstance(content, dict):
        content = json.dumps(content, default=json_serial)
    encoded_content = content.encode()
    return StreamingBody(io.BytesIO(encoded_content), len(encoded_content))


@pytest.mark.parametrize(
    "delim, name, expected",
    [
        ("-", "test-name", "test-name"),
        ("-", "name", "test-name"),
        ("-", "something-name", "test-something-name"),
        ("-", None, "test"),
    ],
)
def test_get_fqn(delim: str, expected: str, name: Optional[str]) -> None:
    """Test runway.context._cfngin.get_fqn."""
    assert get_fqn("test", delim, name) == expected


class TestCFNginContext:
    """Test runway.context._cfngin.CFNginContext."""

    config = CfnginConfig.parse_obj(
        {
            "namespace": "test",
            "stacks": [
                {"name": "stack1", "template_path": "."},
                {"name": "stack2", "template_path": "."},
                {"name": "stack3", "stack_name": "foobar-stack", "template_path": "."},
            ],
        }
    )
    env = DeployEnvironment(explicit_name="test")
    persist_graph_raw_config = {
        "namespace": "test",
        "cfngin_bucket": "cfngin-test",
        "cfngin_bucket_region": "us-east-1",
        "persistent_graph_key": "test.json",
        "stacks": [
            {"name": "stack1", "template_path": "."},
            {"name": "stack2", "template_path": ".", "requires": ["stack1"]},
        ],
    }
    persist_graph_raw: Dict[str, Set[str]] = {"stack1": set(), "stack2": {"stack1"}}
    persist_graph_config = CfnginConfig.parse_obj(persist_graph_raw_config)

    @pytest.mark.parametrize(
        "namespace, expected",
        [
            ("test", "test"),
            ("test-01", "test-01"),
            ("test.01", "test-01"),
            ("Test.01", "test-01"),
        ],
    )
    def test_base_fqn(self, expected: str, namespace: str) -> None:
        """Test base_fqn."""
        obj = CfnginContext(config=CfnginConfig.parse_obj({"namespace": namespace}))
        assert obj.base_fqn == expected

    def test_bucket_name_config(self, mocker: MockerFixture) -> None:
        """Test bucket_name from Config."""
        mocker.patch.object(CfnginContext, "upload_to_s3", True)
        assert (
            CfnginContext(
                config=CfnginConfig.parse_obj({"namespace": "test", "cfngin_bucket": "test-bucket"})
            ).bucket_name
            == "test-bucket"
        )

    def test_bucket_name_generated(self, mocker: MockerFixture) -> None:
        """Test bucket_name generated."""
        mocker.patch.object(CfnginContext, "upload_to_s3", True)
        assert CfnginContext(config=self.config).bucket_name == "cfngin-test-us-east-1"

    def test_bucket_name_none(self, mocker: MockerFixture) -> None:
        """Test bucket_name is None."""
        mocker.patch.object(CfnginContext, "upload_to_s3", False)
        assert CfnginContext().bucket_name is None

    def test_copy(self) -> None:
        """Test copy."""
        obj = CfnginContext(deploy_environment=self.env)
        obj_copy = obj.copy()
        assert obj_copy != obj
        assert obj_copy.config == obj.config
        assert obj_copy.env != obj.env

    def test_get_fqn(self, mocker: MockerFixture) -> None:
        """Test get_fqn."""
        mock_get_fqn = mocker.patch(f"{MODULE}.get_fqn", return_value="success")
        obj = CfnginContext(config=self.config)
        assert obj.get_fqn("name") == "success"
        mock_get_fqn.assert_called_once_with(obj.base_fqn, self.config.namespace_delimiter, "name")

    def test_get_stack(self) -> None:
        """Test get_stack."""
        obj = CfnginContext(config=self.config)
        assert obj.get_stack("test-stack1") == obj.stacks[0]
        # namespace is added if not provided
        assert obj.get_stack("stack1") == obj.stacks[0]
        assert not obj.get_stack("dev-stack1")
        assert not obj.get_stack("stack12")

    def test_get_stack_def_stack_name(self) -> None:
        """Test get_stack stack def has stack_name."""
        obj = CfnginContext(config=self.config)
        assert obj.get_stack("stack3") == obj.stacks[2]
        assert obj.get_stack("foobar-stack") == obj.stacks[2]
        assert obj.get_stack("test-foobar-stack") == obj.stacks[2]

    def test_init(self, tmp_path: Path) -> None:
        """Test init."""
        obj = CfnginContext(
            config=self.config,
            config_path=tmp_path,
            deploy_environment=self.env,
            force_stacks=["stack-01"],
            parameters={"key": "val"},
            stack_names=["stack-02"],
        )
        assert obj.bucket_region == self.env.aws_region
        assert obj.config == self.config
        assert obj.config_path == tmp_path
        assert obj.env == self.env
        assert obj.force_stacks == ["stack-01"]
        assert not obj.hook_data and isinstance(obj.hook_data, dict)
        assert obj.logger
        assert obj.parameters == {"key": "val"}
        assert obj.stack_names == ["stack-02"]

    def test_init_defaults(self) -> None:
        """Test init defaults."""
        obj = CfnginContext()
        assert obj.bucket_region == self.env.aws_region
        assert isinstance(obj.config, CfnginConfig)
        assert obj.config.namespace == "example"
        assert obj.config_path == Path.cwd()
        assert isinstance(obj.env, DeployEnvironment)
        assert obj.force_stacks == []
        assert not obj.hook_data and isinstance(obj.hook_data, dict)
        assert obj.logger
        assert not obj.parameters and isinstance(obj.parameters, dict)
        assert not obj.stack_names and isinstance(obj.stack_names, list)

    def test_lock_persistent_graph_locked(self, mocker: MockerFixture) -> None:
        """Test lock_persistent_graph no graph."""
        mocker.patch.object(CfnginContext, "persistent_graph_locked", True)
        mocker.patch.object(CfnginContext, "persistent_graph", True)
        with pytest.raises(PersistentGraphLocked):
            CfnginContext().lock_persistent_graph("123")

    def test_lock_persistent_graph_no_graph(self, mocker: MockerFixture) -> None:
        """Test lock_persistent_graph no graph."""
        mocker.patch.object(CfnginContext, "persistent_graph", None)
        assert CfnginContext().lock_persistent_graph("123") is None

    def test_lock_persistent_graph_no_such_key(self, mocker: MockerFixture) -> None:
        """Test lock_persistent_graph NoSuchKey."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "persistent_graph_locked", False)
        mocker.patch.object(CfnginContext, "persistent_graph", True)
        obj = CfnginContext()
        stubber = Stubber(obj.s3_client)
        stubber.add_client_error("put_object_tagging", "NoSuchKey")
        with stubber, pytest.raises(PersistentGraphCannotLock):
            obj.lock_persistent_graph("123")

    def test_lock_persistent_graph(self, mocker: MockerFixture) -> None:
        """Test lock_persistent_graph."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "persistent_graph_locked", False)
        mocker.patch.object(CfnginContext, "persistent_graph", True)
        obj = CfnginContext()
        stubber = Stubber(obj.s3_client)
        stubber.add_response(
            "put_object_tagging",
            {},
            {
                "Tagging": {"TagSet": [{"Key": obj._persistent_graph_lock_tag, "Value": "123"}]},
                **obj.persistent_graph_location,
            },
        )
        with stubber:
            assert not obj.lock_persistent_graph("123")

    def test_mappings(self) -> None:
        """Test mappings."""
        config = CfnginConfig.parse_obj(
            {"namespace": "test", "mappings": {"my_map": {"something": {"key": "val"}}}}
        )
        assert CfnginContext(config=config).mappings == config.mappings

    def test_namespace(self) -> None:
        """Test namespace."""
        config = CfnginConfig.parse_obj({"namespace": "test"})
        assert CfnginContext(config=config).namespace == config.namespace

    def test_namespace_delimiter(self) -> None:
        """Test namespace_delimiter."""
        config = CfnginConfig.parse_obj({"namespace": "test", "namespace_delimiter": "."})
        assert CfnginContext(config=config).namespace_delimiter == config.namespace_delimiter

    def test_persistent_graph_no_location(self, mocker: MockerFixture) -> None:
        """Test persistent_graph no persistent_graph_location."""
        mocker.patch.object(CfnginContext, "persistent_graph_location", {})
        assert CfnginContext().persistent_graph is None

    def test_persistent_graph_s3_not_verified(self, mocker: MockerFixture) -> None:
        """Test persistent_graph s3 not verified."""
        mock_graph = mocker.patch(
            f"{MODULE}.Graph", MagicMock(from_dict=MagicMock(return_value="success"))
        )
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "s3_bucket_verified", False)
        obj = CfnginContext()
        assert obj.persistent_graph == "success"
        mock_graph.from_dict.assert_called_once_with({}, obj)

    def test_persistent_graph_no_such_key(self, mocker: MockerFixture) -> None:
        """Test persistent_graph NoSuchKey."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "s3_bucket_verified", True)
        obj = CfnginContext()
        stubber = Stubber(obj.s3_client)

        stubber.add_client_error("get_object", "NoSuchKey")
        stubber.add_response(
            "put_object",
            {},
            {
                "Body": "{}".encode(),
                "ServerSideEncryption": "AES256",
                "ACL": "bucket-owner-full-control",
                "ContentType": "application/json",
                **obj.persistent_graph_location,
            },
        )

        with stubber:
            assert isinstance(obj.persistent_graph, Graph)
            assert obj.persistent_graph.to_dict() == {}

    def test_persistent_graph(self, mocker: MockerFixture) -> None:
        """Test persistent_graph."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "s3_bucket_verified", True)
        obj = CfnginContext()
        stubber = Stubber(obj.s3_client)

        stubber.add_response(
            "get_object",
            {"Body": gen_s3_object_content(self.persist_graph_raw)},
            {
                "ResponseContentType": "application/json",
                **obj.persistent_graph_location,
            },
        )

        with stubber:
            assert isinstance(obj.persistent_graph, Graph)
            assert obj.persistent_graph.to_dict() == self.persist_graph_raw

    def test_persistent_graph_location_add_json(self) -> None:
        """Test persistent_graph_location adds `.json` extension."""
        config = CfnginConfig.parse_obj(
            {
                "namespace": "test",
                "cfngin_bucket": "test-bucket",
                "persistent_graph_key": "something",
            }
        )
        obj = CfnginContext(config=config)
        assert obj.persistent_graph_location.get("Bucket") == config.cfngin_bucket
        assert (
            obj.persistent_graph_location.get("Key")
            == f"persistent_graphs/{config.namespace}/{config.persistent_graph_key}.json"
        )

    @pytest.mark.parametrize(
        "config_ext",
        [
            {"cfngin_bucket": "something"},
            {"cfngin_bucket": "", "persistent_graph_key": "something"},
        ],
    )
    def test_persistent_graph_location_empty(self, config_ext: Dict[str, str]) -> None:
        """Test persistent_graph_location."""
        config = CfnginConfig.parse_obj({"namespace": "test", **config_ext})
        assert not CfnginContext(config=config).persistent_graph_location

    def test_persistent_graph_location(self) -> None:
        """Test persistent_graph_location."""
        config = CfnginConfig.parse_obj(
            {
                "namespace": "test",
                "cfngin_bucket": "test-bucket",
                "persistent_graph_key": "something.json",
            }
        )
        obj = CfnginContext(config=config)
        assert obj.persistent_graph_location.get("Bucket") == config.cfngin_bucket
        assert (
            obj.persistent_graph_location.get("Key")
            == f"persistent_graphs/{config.namespace}/{config.persistent_graph_key}"
        )

    def test_persistent_graph_lock_code_none(self, mocker: MockerFixture) -> None:
        """Test persistent_graph_lock_code None."""
        mocker.patch.object(CfnginContext, "persistent_graph_location", False)
        assert not CfnginContext().persistent_graph_lock_code
        mocker.patch.object(CfnginContext, "persistent_graph_location", True)
        mocker.patch.object(CfnginContext, "persistent_graph_tags", {"key": "val"})
        assert not CfnginContext().persistent_graph_lock_code

    def test_persistent_graph_lock_code(self, mocker: MockerFixture) -> None:
        """Test persistent_graph_lock_code."""
        mocker.patch.object(CfnginContext, "persistent_graph_location", True)
        mocker.patch.object(
            CfnginContext, "persistent_graph_tags", {"cfngin_lock_code": "lock code"}
        )
        assert CfnginContext().persistent_graph_lock_code == "lock code"

    def test_persistent_graph_locked_no_code(self, mocker: MockerFixture) -> None:
        """Test persistent_graph_locked no persistent_graph_lock_code."""
        mocker.patch.object(CfnginContext, "persistent_graph", True)
        mocker.patch.object(CfnginContext, "persistent_graph_lock_code", None)
        assert CfnginContext().persistent_graph_locked is False

    def test_persistent_graph_locked_no_graph(self, mocker: MockerFixture) -> None:
        """Test persistent_graph_locked no persistent_graph."""
        mocker.patch.object(CfnginContext, "persistent_graph", {})
        assert CfnginContext().persistent_graph_locked is False

    def test_persistent_graph_locked(self, mocker: MockerFixture) -> None:
        """Test persistent_graph_locked."""
        mocker.patch.object(CfnginContext, "persistent_graph", True)
        mocker.patch.object(CfnginContext, "persistent_graph_lock_code", "something")
        assert CfnginContext().persistent_graph_locked is True

    def test_persistent_graph_tags_no_such_key(self, mocker: MockerFixture) -> None:
        """Test persistent_graph_tags NoSuchKey."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "persistent_graphs/test/something.json"},
        )
        obj = CfnginContext()
        stubber = Stubber(obj.s3_client)
        stubber.add_client_error("get_object_tagging", "NoSuchKey")
        with stubber:
            assert obj.persistent_graph_tags == {}

    def test_persistent_graph_tags(self, mocker: MockerFixture) -> None:
        """Test persistent_graph_tags."""
        bucket = "test-bucket"
        key = "persistent_graphs/test/something.json"
        mocker.patch.object(
            CfnginContext, "persistent_graph_location", {"Bucket": bucket, "Key": key}
        )
        obj = CfnginContext()
        stubber = Stubber(obj.s3_client)

        stubber.add_response("get_object_tagging", {"TagSet": []}, obj.persistent_graph_location)
        stubber.add_response(
            "get_object_tagging",
            {"TagSet": [{"Key": "key", "Value": "val"}]},
            obj.persistent_graph_location,
        )

        with stubber:
            assert obj.persistent_graph_tags == {}
            assert obj.persistent_graph_tags == {"key": "val"}

    def test_put_persistent_graph_empty(self, mocker: MockerFixture) -> None:
        """Test put_persistent_graph empty."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        obj = CfnginContext()
        obj.persistent_graph = Graph.from_dict({}, context=obj)
        stubber = Stubber(obj.s3_client)
        stubber.add_response("delete_object", {}, obj.persistent_graph_location)
        with stubber:
            assert not obj.put_persistent_graph("123")

    def test_put_persistent_graph_lock_code_mismatch(self, mocker: MockerFixture) -> None:
        """Test put_persistent_graph lock code mismatch."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "persistent_graph_locked", True)
        mocker.patch.object(CfnginContext, "persistent_graph_lock_code", "0")
        obj = CfnginContext()
        obj.persistent_graph = Graph.from_dict(self.persist_graph_raw, context=obj)
        with pytest.raises(PersistentGraphLockCodeMismatch):
            obj.put_persistent_graph("123")

    def test_put_persistent_graph_not_locked(self, mocker: MockerFixture) -> None:
        """Test put_persistent_graph not locked."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "persistent_graph_locked", False)
        obj = CfnginContext()
        obj.persistent_graph = Graph.from_dict(self.persist_graph_raw, context=obj)
        with pytest.raises(PersistentGraphUnlocked):
            obj.put_persistent_graph("123")

    def test_put_persistent_graph_no_graph(self, mocker: MockerFixture) -> None:
        """Test put_persistent_graph n persistent_graph."""
        mocker.patch.object(CfnginContext, "persistent_graph", False)
        assert not CfnginContext().put_persistent_graph("123")

    def test_put_persistent_graph(self, mocker: MockerFixture) -> None:
        """Test put_persistent_graph."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "persistent_graph_locked", True)
        mocker.patch.object(CfnginContext, "persistent_graph_lock_code", "123")
        obj = CfnginContext()
        obj.persistent_graph = Graph.from_dict(self.persist_graph_raw, context=obj)
        stubber = Stubber(obj.s3_client)
        stubber.add_response(
            "put_object",
            {},
            {
                "Body": json.dumps(self.persist_graph_raw, default=json_serial, indent=4).encode(),
                "ServerSideEncryption": "AES256",
                "ACL": "bucket-owner-full-control",
                "ContentType": "application/json",
                "Tagging": "cfngin_lock_code=123",
                **obj.persistent_graph_location,
            },
        )
        with stubber:
            assert not obj.put_persistent_graph("123")

    def test_s3_bucket_verified_no_bucket(self, mocker: MockerFixture) -> None:
        """Test s3_bucket_verified no bucket."""
        mocker.patch.object(CfnginContext, "bucket_name", None)
        assert CfnginContext().s3_bucket_verified is False

    def test_s3_bucket_verified(self, mocker: MockerFixture) -> None:
        """Test s3_bucket_verified."""
        mock_ensure_s3_bucket = mocker.patch(f"{MODULE}.ensure_s3_bucket")
        mocker.patch.object(CfnginContext, "bucket_name", "test-bucket")
        mocker.patch.object(CfnginContext, "persistent_graph_location", {})
        obj = CfnginContext()
        assert obj.s3_bucket_verified is True
        assert obj.s3_bucket_verified is True  # value should be cached
        mock_ensure_s3_bucket.assert_called_once_with(
            obj.s3_client,
            obj.bucket_name,
            obj.bucket_region,
            create=False,
            persist_graph=False,
        )

    def test_s3_client(self, mocker: MockerFixture) -> None:
        """Test s3_client."""
        mock_client = MagicMock()
        mock_session = MagicMock(client=MagicMock(return_value=mock_client))
        mock_get_session = mocker.patch.object(
            CfnginContext, "get_session", return_value=mock_session
        )
        assert CfnginContext(deploy_environment=self.env).s3_client == mock_client
        mock_get_session.assert_called_once_with(region=self.env.aws_region)
        mock_session.client.assert_called_once_with("s3")

    def test_set_hook_data_key_error(self) -> None:
        """Test set_hook_data KeyError."""
        obj = CfnginContext()
        obj.set_hook_data("test", {})
        with pytest.raises(KeyError):
            obj.set_hook_data("test", {"key": "val"})

    @pytest.mark.parametrize("data", ["string", 1, 1.0, ["1"], {"1", "2"}, ("1", "2")])
    def test_set_hook_data_type_error(self, data: Any) -> None:
        """Test set_hook_data TypeError."""
        with pytest.raises(TypeError):
            CfnginContext().set_hook_data("test", data)  # type: ignore

    def test_set_hook_data(self) -> None:
        """Test set_hook_data."""
        obj = CfnginContext()
        obj.set_hook_data("test", {"key": "val"})
        assert obj.hook_data == {"test": {"key": "val"}}

    def test_stacks_dict(self) -> None:
        """Test stacks_dict."""
        obj = CfnginContext(config=self.config)
        assert obj.stacks_dict == {
            "test-stack1": obj.stacks[0],
            "test-stack2": obj.stacks[1],
            "test-foobar-stack": obj.stacks[2],
        }

    def test_stacks(self) -> None:
        """Test stacks."""
        obj = CfnginContext(config=self.config)
        assert len(obj.stacks) == len(self.config.stacks)
        assert isinstance(obj.stacks[0], Stack)
        assert obj.stacks[0].name == self.config.stacks[0].name
        assert isinstance(obj.stacks[1], Stack)
        assert obj.stacks[1].name == self.config.stacks[1].name

    def test_tags_empty(self) -> None:
        """Test tags empty."""
        obj = CfnginContext(config=CfnginConfig.parse_obj({"namespace": "test", "tags": {}}))
        assert obj.tags == {}

    def test_tags_none(self) -> None:
        """Test tags None."""
        obj = CfnginContext(config=CfnginConfig.parse_obj({"namespace": "test", "tags": None}))
        assert obj.tags == {"cfngin_namespace": obj.config.namespace}

    def test_tags(self) -> None:
        """Test tags."""
        obj = CfnginContext(
            config=CfnginConfig.parse_obj({"namespace": "test", "tags": {"key": "val"}})
        )
        assert obj.tags == obj.config.tags

    def test_template_indent(self) -> None:
        """Test template_indent."""
        assert CfnginContext(config=self.config).template_indent == self.config.template_indent

    @pytest.mark.parametrize(
        "config, expected",
        [
            ({"namespace": "test"}, True),
            ({"namespace": ""}, False),
            ({"namespace": "test", "cfngin_bucket": ""}, False),
            ({"namespace": "", "cfngin_bucket": "something"}, True),
            ({"namespace": "test", "cfngin_bucket": "something"}, True),
        ],
    )
    def test_upload_to_s3(self, config: Dict[str, Any], expected: bool) -> None:
        """Test upload_to_s3."""
        assert CfnginContext(config=CfnginConfig.parse_obj(config)).upload_to_s3 is expected

    def test_unlock_persistent_graph_empty_no_such_key(self, mocker: MockerFixture) -> None:
        """Test unlock_persistent_graph empty graph NoSuchKey."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        obj = CfnginContext()
        obj.persistent_graph = Graph.from_dict({}, context=obj)
        stubber = Stubber(obj.s3_client)
        stubber.add_client_error("get_object", "NoSuchKey")
        with stubber:
            assert obj.unlock_persistent_graph("123")

    def test_unlock_persistent_graph_lock_code_mismatch(self, mocker: MockerFixture) -> None:
        """Test unlock_persistent_graph lock code mismatch."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "persistent_graph_locked", True)
        mocker.patch.object(CfnginContext, "persistent_graph_lock_code", "0")
        obj = CfnginContext()
        obj.persistent_graph = Graph.from_dict(self.persist_graph_raw, context=obj)
        with pytest.raises(PersistentGraphCannotUnlock):
            assert obj.unlock_persistent_graph("123")

    def test_unlock_persistent_graph_not_locked(self, mocker: MockerFixture) -> None:
        """Test unlock_persistent_graph."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "persistent_graph_locked", False)
        mocker.patch.object(CfnginContext, "persistent_graph_lock_code", "123")
        obj = CfnginContext()
        obj.persistent_graph = Graph.from_dict(self.persist_graph_raw, context=obj)
        with pytest.raises(PersistentGraphCannotUnlock):
            obj.unlock_persistent_graph("123")

    def test_unlock_persistent_graph_no_graph(self, mocker: MockerFixture) -> None:
        """Test unlock_persistent_graph no graph."""
        mocker.patch.object(CfnginContext, "persistent_graph", False)
        assert CfnginContext().unlock_persistent_graph("123")

    def test_unlock_persistent_graph_no_such_key(self, mocker: MockerFixture) -> None:
        """Test unlock_persistent_graph empty graph NoSuchKey."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "persistent_graph_locked", True)
        mocker.patch.object(CfnginContext, "persistent_graph_lock_code", "123")
        obj = CfnginContext()
        obj.persistent_graph = Graph.from_dict({}, context=obj)
        stubber = Stubber(obj.s3_client)
        stubber.add_response(
            "get_object",
            {"Body": "{}".encode()},
            {
                "ResponseContentType": "application/json",
                **obj.persistent_graph_location,
            },
        )
        stubber.add_client_error("delete_object_tagging", "NoSuchKey")
        with stubber:
            assert obj.unlock_persistent_graph("123")

    @pytest.mark.parametrize("graph_dict", cast(List[Dict[str, List[str]]], [{"stack0": []}, {}]))
    def test_unlock_persistent_graph(
        self, graph_dict: Dict[str, List[str]], mocker: MockerFixture
    ) -> None:
        """Test unlock_persistent_graph."""
        mocker.patch.object(
            CfnginContext,
            "persistent_graph_location",
            {"Bucket": "test-bucket", "Key": "something.json"},
        )
        mocker.patch.object(CfnginContext, "persistent_graph_locked", True)
        mocker.patch.object(CfnginContext, "persistent_graph_lock_code", "123")
        obj = CfnginContext()
        obj.persistent_graph = Graph.from_dict(graph_dict, context=obj)
        stubber = Stubber(obj.s3_client)
        if not graph_dict:
            stubber.add_response(
                "get_object",
                {"Body": "{}".encode()},
                {
                    "ResponseContentType": "application/json",
                    **obj.persistent_graph_location,
                },
            )
        stubber.add_response("delete_object_tagging", {}, obj.persistent_graph_location)
        with stubber:
            assert obj.unlock_persistent_graph("123")
