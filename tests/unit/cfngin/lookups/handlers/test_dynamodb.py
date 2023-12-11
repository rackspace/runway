"""Tests for runway.cfngin.lookups.handlers.dynamodb."""

# pyright: basic
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

import pytest

from runway.cfngin.lookups.handlers.dynamodb import DynamodbLookup, QueryDataModel

if TYPE_CHECKING:
    from ....factories import MockCFNginContext

GET_ITEM_RESPONSE = {
    "Item": {
        "TestKey": {"S": "TestVal"},
        "TestMap": {
            "M": {
                "String1": {"S": "StringVal1"},
                "List1": {"L": [{"S": "ListVal1"}, {"S": "ListVal2"}]},
                "Number1": {"N": "12345"},
            }
        },
        "TestString": {"S": "TestStringVal"},
    }
}


class TestDynamoDBHandler:
    """Test runway.cfngin.lookups.handlers.dynamodb.DynamodbLookup."""

    @pytest.mark.parametrize(
        "query, expected_projection, expected_result",
        [
            (
                "TestTable@TestKey:TestVal.TestString",
                "TestKey,TestString",
                "TestStringVal",
            ),
            (
                "TestTable@TestKey:TestVal[S].TestString",
                "TestKey,TestString",
                "TestStringVal",
            ),
            (
                "TestTable@TestKey:TestVal.TestMap[M].String1",
                "TestKey,TestMap,String1",
                "StringVal1",
            ),
            (
                "TestTable@TestKey:TestVal[S].TestMap[M].String1",
                "TestKey,TestMap,String1",
                "StringVal1",
            ),
        ],
    )
    def test_handle(
        self,
        cfngin_context: MockCFNginContext,
        expected_projection: str,
        expected_result: str,
        query: str,
    ) -> None:
        """Test handle."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": expected_projection,
        }
        stubber.add_response("get_item", GET_ITEM_RESPONSE, expected_params)
        with stubber:
            assert (
                DynamodbLookup.handle(query, context=cfngin_context) == expected_result
            )
        stubber.assert_no_pending_responses()

    def test_handle_client_error(self, cfngin_context: MockCFNginContext) -> None:
        """Test handle ClientError."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"FakeKey": {"S": "TestVal"}},
            "ProjectionExpression": "FakeKey,TestMap,String1",
        }
        stubber.add_client_error(
            "get_item",
            expected_params=expected_params,
        )
        query = "TestTable@FakeKey:TestVal.TestMap[M].String1"
        with stubber, pytest.raises(ValueError) as excinfo:
            DynamodbLookup.handle(query, context=cfngin_context)
        stubber.assert_no_pending_responses()
        assert str(excinfo.value).startswith(
            f"The DynamoDB lookup '{query}' encountered an error: "
        )

    def test_handle_empty_table_name(self, cfngin_context: MockCFNginContext) -> None:
        """Test handle with empty table_name."""
        query = "@TestKey:TestVal.TestMap[M].String1"
        with pytest.raises(ValueError) as excinfo:
            DynamodbLookup.handle(query, context=cfngin_context)
        assert str(excinfo.value).startswith(f"Query '{query}' doesn't match regex:")

    def test_handle_invalid_partition_key(
        self, cfngin_context: MockCFNginContext
    ) -> None:
        """Test handle with invalid partition key."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"FakeKey": {"S": "TestVal"}},
            "ProjectionExpression": "FakeKey,TestMap,String1",
        }
        service_error_code = "ValidationException"
        stubber.add_client_error(
            "get_item",
            service_error_code=service_error_code,
            expected_params=expected_params,
        )

        with stubber, pytest.raises(ValueError) as excinfo:
            DynamodbLookup.handle(
                "TestTable@FakeKey:TestVal.TestMap[M].String1", context=cfngin_context
            )
        stubber.assert_no_pending_responses()
        assert (
            str(excinfo.value)
            == "No DynamoDB record matched the partition key: FakeKey"
        )

    def test_handle_invalid_partition_value(
        self, cfngin_context: MockCFNginContext
    ) -> None:
        """Test handle with invalid partition value."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "FakeVal"}},
            "ProjectionExpression": "TestKey,TestMap,String1",
        }
        empty_response: Dict[str, Any] = {"ResponseMetadata": {}}
        stubber.add_response("get_item", empty_response, expected_params)
        with stubber, pytest.raises(ValueError) as excinfo:
            DynamodbLookup.handle(
                "TestTable@TestKey:FakeVal.TestMap[M].String1", context=cfngin_context
            )
        assert (
            str(excinfo.value)
            == "The DynamoDB record could not be found using the following: "
            "{'TestKey': {'S': 'FakeVal'}}"
        )

    def test_handle_list(self, cfngin_context: MockCFNginContext) -> None:
        """Test handle return list."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestKey,TestMap,List1",
        }
        stubber.add_response("get_item", GET_ITEM_RESPONSE, expected_params)
        with stubber:
            assert DynamodbLookup.handle(
                "TestTable@TestKey:TestVal.TestMap[M].List1[L]", context=cfngin_context
            ) == ["ListVal1", "ListVal2"]
        stubber.assert_no_pending_responses()

    def test_handle_missing_table_name(self, cfngin_context: MockCFNginContext) -> None:
        """Test handle missing table_name."""
        query = "TestKey:TestVal.TestMap[M].String1"
        with pytest.raises(ValueError) as excinfo:
            DynamodbLookup.handle(query, context=cfngin_context)
        assert str(excinfo.value).startswith(
            f"'{query}' missing delimiter for DynamoDB Table name:"
        )

    def test_handle_number(self, cfngin_context: MockCFNginContext) -> None:
        """Test handle return number."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestKey,TestMap,Number1",
        }
        stubber.add_response("get_item", GET_ITEM_RESPONSE, expected_params)
        with stubber:
            assert (
                DynamodbLookup.handle(
                    cfngin_context.env.aws_region
                    + ":TestTable@TestKey:TestVal.TestMap[M].Number1[N]",
                    context=cfngin_context,
                )
                == 12345
            )
        stubber.assert_no_pending_responses()

    def test_handle_table_not_found(self, cfngin_context: MockCFNginContext) -> None:
        """Test handle DDB Table not found."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "FakeTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestKey,TestMap,String1",
        }
        service_error_code = "ResourceNotFoundException"
        stubber.add_client_error(
            "get_item",
            service_error_code=service_error_code,
            expected_params=expected_params,
        )
        with stubber, pytest.raises(ValueError) as excinfo:
            DynamodbLookup.handle(
                "FakeTable@TestKey:TestVal.TestMap[M].String1", context=cfngin_context
            )
        stubber.assert_no_pending_responses()
        assert str(excinfo.value) == "Can't find the DynamoDB table: FakeTable"

    def test_handle_unsupported_data_type(
        self, cfngin_context: MockCFNginContext
    ) -> None:
        """Test handle with unsupported data type."""
        with pytest.raises(ValueError) as excinfo:
            DynamodbLookup.handle(
                "TestTable@TestKey:FakeVal.TestStringSet[B]", context=cfngin_context
            )
        assert (
            str(excinfo.value) == "CFNgin does not support looking up the data type: B"
        )


class TestQueryDataModel:
    """Test runway.cfngin.lookups.handlers.dynamodb.QueryDataModel."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("TestVal", {"S": "TestVal"}),
            ("TestVal[B]", {"B": "TestVal"}),
            ("TestVal[N]", {"N": "TestVal"}),
            ("TestVal[S]", {"S": "TestVal"}),
        ],
    )
    def test_item_key(self, expected: Dict[str, Any], value: str) -> None:
        """Test item_key."""
        assert QueryDataModel(
            attribute="",
            partition_key="TestKey",
            partition_key_value=value,
            table_name="",
        ).item_key == {"TestKey": expected}

    def test_item_key_no_match(self) -> None:
        """Test item_key."""
        obj = QueryDataModel(
            attribute="",
            partition_key="TestKey",
            partition_key_value="TestVal[L]",
            table_name="",
        )
        with pytest.raises(ValueError) as excinfo:
            assert obj.item_key
        assert str(excinfo.value).startswith(
            f"Partition key value '{obj.partition_key_value}' doesn't match regex:"
        )
