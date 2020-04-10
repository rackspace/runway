"""Replicated Lambda Remover State Machine."""
from typing import Any, Dict  # pylint: disable=unused-import

import boto3


def handler(event,  # type: Dict
            _context  # type: Dict
           ):  # noqa: E124
    # type: (...) -> Dict[str, Any]
    """State Machine step to attempt deletion of replicated Lambdas.

    Given a list of Arns will go through each attempting to
    delete. If the resource is not found it will move to the
    next arn, assuming that it has already been deleted. All
    other errors will move the step function to a halt step
    where it will then re-request the deletion process.

    Args:
        event (dict): The AWS Step Function execution event
    """
    arns = event.get('FunctionArns')
    self_destruct = event.get('SelfDestruct')
    lambda_client = boto3.client('lambda')

    # End early if we don't have any arns
    if not arns:
        return {
            'SelfDestruct': self_destruct,
            'FunctionArns': arns,
            'deleted': True,
            'status': 'No Arns To Delete'
        }

    deletions = []

    try:
        # Loop through all arns passed in
        for arn in arns:
            try:
                deletions.append(
                    lambda_client.delete_function(FunctionName=arn)
                )
            # If we can't find the resource then move to the next
            except lambda_client.ResourceNotFoundException:
                continue

        return {
            'SelfDestruct': self_destruct,
            'FunctionArns': arns,
            'deleted': True,
            'deletions': deletions,
            'status': 'Delete Successful'
        }
    # Something went wrong, more than likely the Replicated Function is
    # not currently able to be deleted.
    # https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-edge-delete-replicas.html
    # Try again
    except Exception:  # pylint: disable=broad-except
        return {
            'SelfDestruct': self_destruct,
            'FunctionArns': arns,
            'deleted': False,
            'deletions': deletions,
            'status': 'Delete Failed'
        }
