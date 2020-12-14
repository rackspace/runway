"""Test runway.cfngin.hooks.ecr._purge_repository."""
from typing import TYPE_CHECKING

import boto3
import pytest
from botocore.stub import Stubber

from runway.cfngin.hooks.ecr import purge_repository
from runway.cfngin.hooks.ecr._purge_repository import delete_ecr_images, list_ecr_images

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from ....factories import MockCFNginContext

MODULE = "runway.cfngin.hooks.ecr._purge_repository"


def test_delete_ecr_images():
    """Test delete_ecr_images."""
    client = boto3.client("ecr")
    stubber = Stubber(client)
    image_ids = [{"imageDigest": "image0"}]
    repo_name = "test-repo"

    stubber.add_response(
        "batch_delete_image",
        {"imageIds": image_ids, "failures": []},
        {"repositoryName": repo_name, "imageIds": image_ids},
    )

    with stubber:
        assert not delete_ecr_images(
            client, image_ids=image_ids, repository_name=repo_name
        )


def test_delete_ecr_images_failures():
    """Test delete_ecr_images with failures."""
    client = boto3.client("ecr")
    stubber = Stubber(client)
    image_ids = [{"imageDigest": "image0"}]
    repo_name = "test-repo"

    stubber.add_response(
        "batch_delete_image",
        {
            "imageIds": image_ids,
            "failures": [
                {
                    "imageId": {"imageDigest": "abc123"},
                    "failureCode": "InvalidImageDigest",
                    "failureReason": "reason",
                }
            ],
        },
        {"repositoryName": repo_name, "imageIds": image_ids},
    )

    with stubber, pytest.raises(ValueError):
        delete_ecr_images(client, image_ids=image_ids, repository_name=repo_name)


def test_list_ecr_images():
    """Test list_ecr_images."""
    client = boto3.client("ecr")
    stubber = Stubber(client)
    repo_name = "test-repo"
    next_token = "abc123"

    stubber.add_response(
        "list_images",
        {
            "imageIds": [{"imageDigest": "image0"}, {"imageTag": "image1"}],
            "nextToken": next_token,
        },
        {"filter": {"tagStatus": "ANY"}, "repositoryName": repo_name},
    )
    stubber.add_response(
        "list_images",
        {"imageIds": [{"imageDigest": "image2"}]},
        {
            "filter": {"tagStatus": "ANY"},
            "nextToken": next_token,
            "repositoryName": repo_name,
        },
    )

    with stubber:
        result = list_ecr_images(client, repository_name=repo_name)
        # order in response is not maintained so testing membership rather than equality
        assert len(result) == 2
        assert {"imageDigest": "image0"} in result
        assert {"imageDigest": "image2"} in result


def test_list_ecr_images_repository_not_found():
    """Test list_ecr_images RepositoryNotFoundException."""
    client = boto3.client("ecr")
    stubber = Stubber(client)

    stubber.add_client_error("list_images", "RepositoryNotFoundException")
    with stubber:
        assert list_ecr_images(client, repository_name="test-repo") == []


def test_purge_repository(
    cfngin_context,  # type: "MockCFNginContext"
    mocker,  # type: "MockerFixture"
):  # type: (...) -> None
    """Test purge_repository."""
    mock_list_ecr_images = mocker.patch(
        MODULE + ".list_ecr_images", return_value=[{"imageDigest": "abc123"}]
    )
    mock_delete_ecr_images = mocker.patch(MODULE + ".delete_ecr_images")
    cfngin_context.add_stubber("ecr")
    client = cfngin_context.get_session().client("ecr")
    repo_name = "test-repo"

    assert purge_repository(cfngin_context, repository_name=repo_name) == {
        "status": "success"
    }
    mock_list_ecr_images.assert_called_once_with(client, repository_name=repo_name)
    mock_delete_ecr_images.assert_called_once_with(
        client, image_ids=mock_list_ecr_images.return_value, repository_name=repo_name
    )


def test_purge_repository_skip(
    cfngin_context,  # type: "MockCFNginContext"
    mocker,  # type: "MockerFixture"
):  # type: (...) -> None
    """Test purge_repository."""
    mock_list_ecr_images = mocker.patch(MODULE + ".list_ecr_images", return_value=[])
    mock_delete_ecr_images = mocker.patch(MODULE + ".delete_ecr_images")
    cfngin_context.add_stubber("ecr")
    client = cfngin_context.get_session().client("ecr")
    repo_name = "test-repo"

    assert purge_repository(cfngin_context, repository_name=repo_name) == {
        "status": "skipped"
    }
    mock_list_ecr_images.assert_called_once_with(client, repository_name=repo_name)
    mock_delete_ecr_images.assert_not_called()
