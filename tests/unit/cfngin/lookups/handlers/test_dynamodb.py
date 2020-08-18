"""Tests for runway.cfngin.lookups.handlers.dynamodb."""
import unittest

import boto3
import mock
from botocore.stub import Stubber

from runway.cfngin.lookups.handlers.dynamodb import DynamodbLookup

from ...factories import SessionStub


class TestDynamoDBHandler(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.dynamodb.DynamodbLookup."""

    client = boto3.client(
        "dynamodb",
        region_name="us-east-1",
        # bypass the need to have these in the env
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )

    def setUp(self):
        """Run before tests."""
        self.stubber = Stubber(self.client)
        self.get_parameters_response = {
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

    @mock.patch(
        "runway.cfngin.lookups.handlers.dynamodb.get_session",
        return_value=SessionStub(client),
    )
    def test_dynamodb_handler(self, _mock_client):
        """Test DynamoDB handler."""
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,String1",
        }
        self.stubber.add_response(
            "get_item", self.get_parameters_response, expected_params
        )
        with self.stubber:
            base_lookup_key = "TestTable@TestKey:TestVal.TestMap[M].String1"
            value = DynamodbLookup.handle(base_lookup_key)
            base_lookup_key_valid = "StringVal1"
            self.assertEqual(value, base_lookup_key_valid)

    @mock.patch(
        "runway.cfngin.lookups.handlers.dynamodb.get_session",
        return_value=SessionStub(client),
    )
    def test_dynamodb_number_handler(self, _mock_client):
        """Test DynamoDB number handler."""
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,Number1",
        }
        self.stubber.add_response(
            "get_item", self.get_parameters_response, expected_params
        )
        with self.stubber:
            base_lookup_key = "TestTable@TestKey:TestVal.TestMap[M].Number1[N]"
            value = DynamodbLookup.handle(base_lookup_key)
            base_lookup_key_valid = 12345
            self.assertEqual(value, base_lookup_key_valid)

    @mock.patch(
        "runway.cfngin.lookups.handlers.dynamodb.get_session",
        return_value=SessionStub(client),
    )
    def test_dynamodb_list_handler(self, _mock_client):
        """Test DynamoDB list handler."""
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,List1",
        }
        self.stubber.add_response(
            "get_item", self.get_parameters_response, expected_params
        )
        with self.stubber:
            base_lookup_key = "TestTable@TestKey:TestVal.TestMap[M].List1[L]"
            value = DynamodbLookup.handle(base_lookup_key)
            base_lookup_key_valid = ["ListVal1", "ListVal2"]
            self.assertEqual(value, base_lookup_key_valid)

    @mock.patch(
        "runway.cfngin.lookups.handlers.dynamodb.get_session",
        return_value=SessionStub(client),
    )
    def test_dynamodb_empty_table_handler(self, _mock_client):
        """Test DynamoDB empty table handler."""
        expected_params = {
            "TableName": "",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,String1",
        }
        self.stubber.add_response(
            "get_item", self.get_parameters_response, expected_params
        )
        with self.stubber:
            base_lookup_key = "@TestKey:TestVal.TestMap[M].String1"
            try:
                DynamodbLookup.handle(base_lookup_key)
            except ValueError as err:
                self.assertEqual(
                    "Please make sure to include a DynamoDB table name", str(err)
                )

    @mock.patch(
        "runway.cfngin.lookups.handlers.dynamodb.get_session",
        return_value=SessionStub(client),
    )
    def test_dynamodb_missing_table_handler(self, _mock_client):
        """Test DynamoDB missing table handler."""
        expected_params = {
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,String1",
        }
        self.stubber.add_response(
            "get_item", self.get_parameters_response, expected_params
        )
        with self.stubber:
            base_lookup_key = "TestKey:TestVal.TestMap[M].String1"
            try:
                DynamodbLookup.handle(base_lookup_key)
            except ValueError as err:
                self.assertEqual("Please make sure to include a tablename", str(err))

    @mock.patch(
        "runway.cfngin.lookups.handlers.dynamodb.get_session",
        return_value=SessionStub(client),
    )
    def test_dynamodb_invalid_table_handler(self, _mock_client):
        """Test DynamoDB invalid table handler."""
        expected_params = {
            "TableName": "FakeTable",
            "Key": {"TestKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,String1",
        }
        service_error_code = "ResourceNotFoundException"
        self.stubber.add_client_error(
            "get_item",
            service_error_code=service_error_code,
            expected_params=expected_params,
        )
        with self.stubber:
            base_lookup_key = "FakeTable@TestKey:TestVal.TestMap[M].String1"
            try:
                DynamodbLookup.handle(base_lookup_key)
            except ValueError as err:
                self.assertEqual("Cannot find the DynamoDB table: FakeTable", str(err))

    @mock.patch(
        "runway.cfngin.lookups.handlers.dynamodb.get_session",
        return_value=SessionStub(client),
    )
    def test_dynamodb_invalid_partition_key_handler(self, _mock_client):
        """Test DynamoDB invalid partition key handler."""
        expected_params = {
            "TableName": "TestTable",
            "Key": {"FakeKey": {"S": "TestVal"}},
            "ProjectionExpression": "TestVal,TestMap,String1",
        }
        service_error_code = "ValidationException"
        self.stubber.add_client_error(
            "get_item",
            service_error_code=service_error_code,
            expected_params=expected_params,
        )

        with self.stubber:
            base_lookup_key = "TestTable@FakeKey:TestVal.TestMap[M].String1"
            try:
                DynamodbLookup.handle(base_lookup_key)
            except ValueError as err:
                self.assertEqual(
                    "No DynamoDB record matched the partition key: FakeKey", str(err)
                )

    @mock.patch(
        "runway.cfngin.lookups.handlers.dynamodb.get_session",
        return_value=SessionStub(client),
    )
    def test_dynamodb_invalid_partition_val_handler(self, _mock_client):
        """Test DynamoDB invalid partition val handler."""
        expected_params = {
            "TableName": "TestTable",
            "Key": {"TestKey": {"S": "FakeVal"}},
            "ProjectionExpression": "FakeVal,TestMap,String1",
        }
        empty_response = {"ResponseMetadata": {}}
        self.stubber.add_response("get_item", empty_response, expected_params)
        with self.stubber:
            base_lookup_key = "TestTable@TestKey:FakeVal.TestMap[M].String1"
            try:
                DynamodbLookup.handle(base_lookup_key)
            except ValueError as err:
                self.assertEqual(
                    "The DynamoDB record could not be found using "
                    "the following key: {'S': 'FakeVal'}",
                    str(err),
                )
