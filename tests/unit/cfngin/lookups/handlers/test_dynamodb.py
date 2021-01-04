"""Tests for runway.cfngin.lookups.handlers.dynamodb."""
# pylint: disable=no-self-use
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from runway.cfngin.lookups.handlers.dynamodb import DynamodbLookup

if TYPE_CHECKING:
    from ....factories import MockCFNginContext

GET_ITEM_RESPONSE = {
    "Item": {
        "TestMap": {
            "M": {
                "String1": {"S": "StringVal1"},
                "List1": {"L": [{"S": "ListVal1"}, {"S": "ListVal2"}]},
                "Number1": {"N": "12345"},
            }
        }
    }
}


class TestDynamoDBHandler:
    """Tests for runway.cfngin.lookups.handlers.dynamodb.DynamodbLookup."""

    client = None

    def test_dynamodb_handler(self, cfngin_context: MockCFNginContext) -> None:
        """Test DynamoDB handler."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,String1",
        }
        stubber.add_response("get_item", GET_ITEM_RESPONSE, expected_params)
        with stubber:
            assert (
                DynamodbLookup.handle(
                    "TestTable@TestKey:TestVal.TestMap[M].String1",
                    context=cfngin_context,
                )
                == "StringVal1"
            )

    def test_dynamodb_number_handler(self, cfngin_context: MockCFNginContext) -> None:
        """Test DynamoDB number handler."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,Number1",
        }
        stubber.add_response("get_item", GET_ITEM_RESPONSE, expected_params)
        with stubber:
            assert (
                DynamodbLookup.handle(
                    "TestTable@TestKey:TestVal.TestMap[M].Number1[N]",
                    context=cfngin_context,
                )
                == 12345
            )

    def test_dynamodb_list_handler(self, cfngin_context: MockCFNginContext) -> None:
        """Test DynamoDB list handler."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,List1",
        }
        stubber.add_response("get_item", GET_ITEM_RESPONSE, expected_params)
        with stubber:
            assert DynamodbLookup.handle(
                "TestTable@TestKey:TestVal.TestMap[M].List1[L]", context=cfngin_context
            ) == ["ListVal1", "ListVal2"]

    def test_dynamodb_empty_table_handler(
        self, cfngin_context: MockCFNginContext
    ) -> None:
        """Test DynamoDB empty table handler."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,String1",
        }
        stubber.add_response("get_item", GET_ITEM_RESPONSE, expected_params)
        with stubber, pytest.raises(ValueError) as excinfo:
            DynamodbLookup.handle(
                "@TestKey:TestVal.TestMap[M].String1", context=cfngin_context
            )
        assert str(excinfo.value) == "Please make sure to include a DynamoDB table name"

    def test_dynamodb_missing_table_handler(
        self, cfngin_context: MockCFNginContext
    ) -> None:
        """Test DynamoDB missing table handler."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,String1",
        }
        stubber.add_response("get_item", GET_ITEM_RESPONSE, expected_params)
        with stubber, pytest.raises(ValueError) as excinfo:
            DynamodbLookup.handle(
                "TestKey:TestVal.TestMap[M].String1", context=cfngin_context
            )
        assert str(excinfo.value) == "Please make sure to include a tablename"

    def test_dynamodb_invalid_table_handler(
        self, cfngin_context: MockCFNginContext
    ) -> None:
        """Test DynamoDB invalid table handler."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "FakeTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,String1",
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
        assert str(excinfo.value) == "Cannot find the DynamoDB table: FakeTable"

    def test_dynamodb_invalid_partition_key_handler(
        self, cfngin_context: MockCFNginContext
    ) -> None:
        """Test DynamoDB invalid partition key handler."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"FakeKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,String1",
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
        assert (
            str(excinfo.value)
            == "No DynamoDB record matched the partition key: FakeKey"
        )

    def test_dynamodb_invalid_partition_val_handler(
        self, cfngin_context: MockCFNginContext
    ) -> None:
        """Test DynamoDB invalid partition val handler."""
        stubber = cfngin_context.add_stubber("dynamodb")
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "FakeVal"}},
            "ProjectionExpression": "FakeVal,TestMap,String1",
        }
        empty_response = {"ResponseMetadata": {}}
        stubber.add_response("get_item", empty_response, expected_params)
        with stubber, pytest.raises(ValueError) as excinfo:
            DynamodbLookup.handle(
                "TestTable@TestKey:FakeVal.TestMap[M].String1", context=cfngin_context
            )
        assert (
            str(excinfo.value)
            == "The DynamoDB record could not be found using the following key: {'S': 'FakeVal'}"
        )
