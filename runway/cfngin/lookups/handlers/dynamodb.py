"""DynamoDB lookup."""
# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from botocore.exceptions import ClientError
from typing_extensions import Literal, TypedDict

from ....lookups.handlers.base import LookupHandler
from ...utils import read_value_from_path

if TYPE_CHECKING:
    from ....context import CfnginContext

TYPE_NAME = "dynamodb"


class DynamodbLookup(LookupHandler):
    """DynamoDB lookup."""

    @classmethod
    def handle(  # pylint: disable=arguments-differ
        cls, value: str, context: CfnginContext, *__args: Any, **__kwargs: Any
    ) -> Any:
        """Get a value from a DynamoDB table.

        Args:
            value: Parameter(s) given to this lookup.
                ``[<region>:]<tablename>@<primarypartionkey>:<keyvalue>.<keyvalue>...``
            context: Context instance.

        .. note:: The region is optional, and defaults to the environment's
                  ``AWS_DEFAULT_REGION`` if not specified.

        """
        value = read_value_from_path(value)
        table_info = None
        table_keys = None
        region = None
        table_name = None
        if "@" not in value:
            raise ValueError("Please make sure to include a tablename")

        table_info, table_keys = value.split("@", 1)
        if ":" in table_info:
            region, table_name = table_info.split(":", 1)
        else:
            table_name = table_info
        if not table_name:
            raise ValueError("Please make sure to include a DynamoDB table name")

        table_lookup, table_keys = table_keys.split(":", 1)

        table_keys = table_keys.split(".")

        key_dict = _lookup_key_parse(table_keys)
        new_keys = key_dict["new_keys"]
        clean_table_keys = key_dict["clean_table_keys"]

        projection_expression = _build_projection_expression(clean_table_keys)

        # lookup the data from DynamoDB
        dynamodb = context.get_session(region=region).client("dynamodb")
        try:
            response = dynamodb.get_item(
                TableName=table_name,
                Key={table_lookup: new_keys[0]},
                ProjectionExpression=projection_expression,
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceNotFoundException":
                raise ValueError(
                    f"Cannot find the DynamoDB table: {table_name}"
                ) from exc
            if exc.response["Error"]["Code"] == "ValidationException":
                raise ValueError(
                    f"No DynamoDB record matched the partition key: {table_lookup}"
                ) from exc
            raise ValueError(
                f"The DynamoDB lookup {value} had an error: {exc}"
            ) from exc
        # find and return the key from the dynamo data returned
        if "Item" in response:
            return _get_val_from_ddb_data(response["Item"], new_keys[1:])
        raise ValueError(
            f"The DynamoDB record could not be found using the following key: {new_keys[0]}"
        )


class ParsedLookupKey(TypedDict):
    """Return value of _lookup_key_parse."""

    clean_table_keys: List[str]
    new_keys: List[Dict[Literal["L", "M", "N", "S"], str]]


def _lookup_key_parse(table_keys: List[str]) -> ParsedLookupKey:
    """Return the order in which the stacks should be executed.

    Args:
        table_keys: List of keys a table.

    Returns:
        Includes a dict of lookup types with data types ('new_keys')
        and a list of the lookups with without ('clean_table_keys')

    """
    # we need to parse the key lookup passed in
    regex_matcher = r"\[([^\]]+)]"
    valid_dynamodb_datatypes = ["L", "M", "N", "S"]
    clean_table_keys: List[str] = []
    new_keys: List[Dict[Literal["L", "M", "N", "S"], str]] = []

    for key in table_keys:
        match = re.search(regex_matcher, key)
        if match:
            # the datatypes are pulled from the dynamodb docs
            if match.group(1) not in valid_dynamodb_datatypes:
                raise ValueError(
                    ("CFNgin does not support looking up the datatype: {}").format(
                        str(match.group(1))
                    )
                )
            match_val = cast(Literal["L", "M", "N", "S"], match.group(1))
            key = key.replace(match.group(0), "")
            new_keys.append({match_val: key})
        else:
            new_keys.append({"S": key})
        clean_table_keys.append(key)
    return {"new_keys": new_keys, "clean_table_keys": clean_table_keys}


def _build_projection_expression(clean_table_keys: List[str]) -> str:
    """Return a projection expression for the DynamoDB lookup.

    Args:
        clean_table_keys: Keys without the data types attached.

    Returns:
        str: A projection expression for the DynamoDB lookup.

    """
    projection_expression = "".join(
        ("{},").format(key) for key in clean_table_keys[:-1]
    )

    projection_expression += clean_table_keys[-1]
    return projection_expression


def _get_val_from_ddb_data(data: Dict[str, Any], keylist: List[Dict[str, str]]) -> Any:
    """Return the value of the lookup.

    Args:
        data: The raw DynamoDB data.
        keylist: A list of keys to lookup. This must include the datatype.

    Returns:
        The value from the DynamoDB record, and casts it to a matching python
        datatype.

    """
    next_type: Optional[str] = None
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
        # TODO: handle various types of 'number' datatypes, (e.g. int, double)
        # if a number, convert to an int and return
        return int(data[cast(str, next_type)])
    # else, just assume its a string and return
    return str(data[cast(str, next_type)])


def _convert_ddb_list_to_list(conversion_list: List[Dict[str, Any]]) -> List[Any]:
    """Return a python list without the DynamoDB datatypes.

    Args:
        conversion_list: A DynamoDB list which includes the datatypes.

    Returns:
        Returns A sanitized list without the datatypes.

    """
    ret_list: List[Any] = []
    for val in conversion_list:
        for v in val:
            ret_list.append(val[v])
    return ret_list
