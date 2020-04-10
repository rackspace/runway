"""Self Destruction Lambda."""
from typing import Any, Dict, Union  # pylint: disable=unused-import

import boto3


def handler(event,  # type: Dict
            _context  # type: Dict
           ):  # noqa: E124
    # type: (...) -> Union[Dict[str, Any], bool]
    """Self destruct the stack.

    Execute self destruction of the stack this lambda is a part of.

    Args:
        event (dict): The AWS Step Function execution event
    """
    data = event.get('SelfDestruct')
    cfn_client = boto3.client('cloudformation')

    if not data:
        return False

    deleted_stack = cfn_client.delete_stack(StackName=data.get('StackName'))

    return {'deleted_stack': deleted_stack}
