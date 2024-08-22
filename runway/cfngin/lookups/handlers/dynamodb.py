"""DynamoDB lookup."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, ClassVar, cast

from botocore.exceptions import ClientError
from typing_extensions import Literal, TypedDict

from ....lookups.handlers.base import LookupHandler
from ....utils import BaseModel
from ...utils import read_value_from_path

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.type_defs import AttributeValueTypeDef

    from ....context import CfnginContext
    from ....lookups.handlers.base import ParsedArgsTypeDef


_QUERY_PATTERN = r"""(?x)  # <table_name>@<partition_key>:<partition_key_value>.<attribute>
^(?P<table_name>[a-zA-Z0-9\-_\.]{3,255})  # name of the DynamoDB Table
@  # delimiter
(?P<partition_key>\S*)  # partition/primary key
:  # delimiter
(?P<partition_key_value>[^\.]*)  # value of partition/primary key
\.  # delimiter
(?P<attribute>.*)$  # attribute to get
"""
"""Lookup query pattern minus region argument.

.. note::
    This pattern and/or it's variable will likely change in a future release so it
    should not be consumed directly by any external code.

"""


class ArgsDataModel(BaseModel):
    """Arguments data model."""

    region: str | None = None
    """AWS region."""


class QueryDataModel(BaseModel):
    """Arguments data model."""

    attribute: str
    """The attribute to be returned by this lookup.
    Supports additional syntax to retrieve a nested value.

    """

    partition_key: str
    """The DynamoDB Table's partition key."""

    partition_key_value: str
    """The value of the partition key to query the database."""

    table_name: str
    """Name of the DynamoDB Table to query."""

    @property
    def item_key(self) -> dict[str, AttributeValueTypeDef]:
        """Value to pass to boto3 ``.get_item()`` call as the ``Key`` argument.

        Raises:
            ValueError: The value of ``partition_key_value`` doesn't match the
                required regex and so it can't be parsed.

        """
        pattern = re.compile(r"^(?P<value>[^\[]+)\[?(?P<data_type>[BNS]+)?]?$")
        match = pattern.search(self.partition_key_value)
        if not match:
            raise ValueError(
                f"Partition key value '{self.partition_key_value}' "
                f"doesn't match regex: {pattern.pattern}"
            )
        return {
            self.partition_key: cast(
                "AttributeValueTypeDef",
                {match.groupdict("S")["data_type"]: match.group("value")},
            )
        }


class DynamodbLookup(LookupHandler["CfnginContext"]):
    """DynamoDB lookup."""

    TYPE_NAME: ClassVar[str] = "dynamodb"
    """Name that the Lookup is registered as."""

    @classmethod
    def parse(cls, value: str) -> tuple[str, ParsedArgsTypeDef]:
        """Parse the value passed to the lookup.

        This overrides the default parsing to account for special requirements.

        Args:
            value: The raw value passed to a lookup.

        Returns:
            The lookup query and a dict of arguments

        Raises:
            ValueError: The value provided does not appear to contain the name of
                a DynamoDB Table. The name of a Table is required.

        """
        raw_value = read_value_from_path(value)
        args: ParsedArgsTypeDef = {}

        if "@" not in raw_value:
            raise ValueError(
                f"'{raw_value}' missing delimiter for DynamoDB Table name:\n{_QUERY_PATTERN}"
            )

        table_info, table_keys = raw_value.split("@", 1)
        if ":" in table_info:
            args["region"], table_info = table_info.split(":", 1)

        return f"{table_info}@{table_keys}", args

    @classmethod
    def parse_query(cls, value: str) -> QueryDataModel:
        """Parse query string to extract. Does not support arguments in ``value``.

        Raises:
            ValueError: The argument provided does not match the expected format defined
                with a regex pattern.

        """
        # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html
        pattern = re.compile(_QUERY_PATTERN)
        match = pattern.search(value)
        if not match:
            raise ValueError(f"Query '{value}' doesn't match regex:\n{pattern.pattern}")
        return QueryDataModel.model_validate(match.groupdict())

    @classmethod
    def handle(cls, value: str, context: CfnginContext, *__args: Any, **__kwargs: Any) -> Any:
        """Get a value from a DynamoDB table.

        Args:
            value: Parameter(s) given to this lookup.
                ``[<region>:]<tablename>@<partitionkey>:<keyvalue>.<keyvalue>...``
            context: Context instance.

        Raises:
            ValueError: The value provided to the lookup resulted in an error.

        .. note:: The region is optional, and defaults to the environment's
                  ``AWS_DEFAULT_REGION`` if not specified.

        """
        raw_query, raw_args = cls.parse(value)
        query = cls.parse_query(raw_query)
        args = ArgsDataModel.model_validate(raw_args)

        table_keys = query.attribute.split(".")

        key_dict = _lookup_key_parse(table_keys)

        dynamodb = context.get_session(region=args.region).client("dynamodb")
        try:
            response = dynamodb.get_item(
                TableName=query.table_name,
                Key=query.item_key,
                ProjectionExpression=",".join([query.partition_key, *key_dict["clean_table_keys"]]),
            )
        except dynamodb.exceptions.ResourceNotFoundException as exc:
            raise ValueError(f"Can't find the DynamoDB table: {query.table_name}") from exc
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ValidationException":
                raise ValueError(
                    f"No DynamoDB record matched the partition key: {query.partition_key}"
                ) from exc
            raise ValueError(f"The DynamoDB lookup '{value}' encountered an error: {exc}") from exc
        # find and return the key from the dynamo data returned
        if "Item" in response:
            return _get_val_from_ddb_data(response["Item"], key_dict["new_keys"])
        raise ValueError(
            f"The DynamoDB record could not be found using the following: {query.item_key}"
        )


class ParsedLookupKey(TypedDict):
    """Return value of _lookup_key_parse."""

    clean_table_keys: list[str]
    new_keys: list[dict[Literal["L", "M", "N", "S"], str]]


def _lookup_key_parse(table_keys: list[str]) -> ParsedLookupKey:
    """Return the order in which the stacks should be executed.

    Args:
        table_keys: List of keys a table.

    Returns:
        Includes a dict of lookup types with data types ('new_keys')
        and a list of the lookups without ('clean_table_keys')

    Raises:
        ValueError: DynamoDB data type is not supported.

    """
    # we need to parse the key lookup passed in
    regex_matcher = r"\[([^\]]+)]"
    valid_dynamodb_datatypes = ["L", "M", "N", "S"]
    clean_table_keys: list[str] = []
    new_keys: list[dict[Literal["L", "M", "N", "S"], str]] = []

    for key in table_keys:
        match = re.search(regex_matcher, key)
        if match:
            # the datatypes are pulled from the dynamodb docs
            if match.group(1) not in valid_dynamodb_datatypes:
                raise ValueError(
                    f"CFNgin does not support looking up the data type: {match.group(1)}"
                )
            match_val = cast(Literal["L", "M", "N", "S"], match.group(1))
            key = key.replace(match.group(0), "")  # noqa: PLW2901
            new_keys.append({match_val: key})
        else:
            new_keys.append({"S": key})
        clean_table_keys.append(key)
    return {"new_keys": new_keys, "clean_table_keys": clean_table_keys}


def _get_val_from_ddb_data(
    data: dict[str, Any], keylist: list[dict[Literal["L", "M", "N", "S"], str]]
) -> Any:
    """Return the value of the lookup.

    Args:
        data: The raw DynamoDB data.
        keylist: A list of keys to lookup. This must include the datatype.

    Returns:
        The value from the DynamoDB record, and casts it to a matching python
        datatype.

    """
    next_type: str | None = None
    # iterate through the keylist to find the matching key/datatype
    for key in keylist:
        for k in key:
            if next_type is None:
                data = data[key[k]]
            else:
                temp_dict = data[next_type]
                data = temp_dict[key[k]]
            next_type = k
    if next_type == "L":
        # if type is list, convert it to a list and return
        return _convert_ddb_list_to_list(data[cast(str, next_type)])
    if next_type == "N":
        # TODO (troyready): handle various types of 'number' datatypes, (e.g. int, double)
        # if a number, convert to an int and return
        return int(data[cast(str, next_type)])
    # else, just assume its a string and return
    return str(data[cast(str, next_type)])


def _convert_ddb_list_to_list(conversion_list: list[dict[str, Any]]) -> list[Any]:
    """Return a python list without the DynamoDB datatypes.

    Args:
        conversion_list: A DynamoDB list which includes the datatypes.

    Returns:
        Returns A sanitized list without the datatypes.

    """
    return [val[v] for val in conversion_list for v in val]
