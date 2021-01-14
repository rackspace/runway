"""Purge all images from an ECR repository.

.. rubric:: Hook Path

``runway.cfngin.hooks.ecr.purge_repository``

.. rubric:: Args

repository_name (str)
    The name of the ECR repository to purge.

.. rubric:: Example
.. code-block:: yaml

    pre_destroy:
      - path: runway.cfngin.hooks.ecr.purge_repository
        args:
          repository_name: example-repo

"""
import logging
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from mypy_boto3_ecr.client import ECRClient  # pylint: disable=E
    from mypy_boto3_ecr.type_defs import ImageIdentifierTypeDef  # pylint: disable=E

    from ...context import Context

LOGGER = logging.getLogger(__name__.replace("._", "."))


def delete_ecr_images(
    client,  # type: ECRClient
    image_ids,  # type: List["ImageIdentifierTypeDef"]
    repository_name,  # type: str
):  # type: (...) -> None
    """Delete images from an ECR repository."""
    response = client.batch_delete_image(
        repositoryName=repository_name, imageIds=image_ids
    )
    if response.get("failures"):
        for msg in response["failures"]:
            LOGGER.info(
                "failed to delete image %s: (%s) %s",
                msg["imageId"].get("imageDigest") or msg["imageId"].get("imageTag"),
                msg["failureCode"],
                msg["failureReason"],
            )
        raise ValueError("failures present in response")


def list_ecr_images(
    client,  # type: "ECRClient"
    repository_name,  # type: str
):  # type: (...) -> List["ImageIdentifierTypeDef"]
    """List all images in an ECR repository."""
    image_ids = []
    try:
        response = client.list_images(
            repositoryName=repository_name, filter={"tagStatus": "ANY"}
        )
        image_ids.extend(response["imageIds"])
        while response.get("nextToken"):
            response = client.list_images(
                filter={"tagStatus": "ANY"},
                nextToken=response["nextToken"],
                repositoryName=repository_name,
            )
            image_ids.extend(response["imageIds"])
        return [
            {"imageDigest": digest}
            for digest in {
                image["imageDigest"] for image in image_ids if image.get("imageDigest")
            }
        ]
    except client.exceptions.RepositoryNotFoundException:
        LOGGER.info("repository %s does not exist", repository_name)
        return []


def purge_repository(
    context,  # type: "Context"
    repository_name,  # type: str
    **_  # type: Any
):  # type: (...) -> Dict[str, str]
    """Purge all images from an ECR repository."""
    client = context.get_session().client("ecr")
    image_ids = list_ecr_images(client, repository_name=repository_name)
    if not image_ids:
        LOGGER.info("no images found in repository %s", repository_name)
        return {"status": "skipped"}
    delete_ecr_images(client, image_ids=image_ids, repository_name=repository_name)
    LOGGER.info("purged all images from repository")
    return {"status": "success"}
