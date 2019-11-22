#!/usr/bin/env python
"""Clean out old ECR images."""
from builtins import input  # pylint: disable=redefined-builtin

import os
import logging

import boto3

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
IMAGES_TO_RETAIN = int(os.environ.get('IMAGES_TO_RETAIN', '75'))


def handler(event, context):  # pylint: disable=unused-argument
    """Lambda entry point."""
    LOGGER.info('Retrieving current image tag from parameter %s',
                SSM_PARAM)
    ssm_client = boto3.client('ssm')
    current_tag = ssm_client.get_parameter(
        Name=SSM_PARAM
    )['Parameter']['Value']
    LOGGER.info('Current task tag is %s', current_tag)

    LOGGER.info('Looking up ECR images from repo %s', REPO_NAME)
    ecr_client = boto3.client('ecr')
    images = []
    paginator = ecr_client.get_paginator('describe_images')
    response_iterator = paginator.paginate(
        repositoryName=REPO_NAME,
        filter={'tagStatus': 'TAGGED'}
    )
    for page in response_iterator:
        images.extend(page.get('imageDetails', []))

    images = sorted(images, key=lambda k: k['imagePushedAt'])
    if len(images) > IMAGES_TO_RETAIN:
        images_to_delete = [i['imageDigest']
                            for i in images[:len(images) - IMAGES_TO_RETAIN]
                            if current_tag not in i.get('imageTags', [])]
        LOGGER.info("Deleting images %s",
                    ','.join(images_to_delete))
        ecr_client.batch_delete_image(
            repositoryName=REPO_NAME,
            imageIds=[{'imageDigest': i} for i in images_to_delete]
        )
    else:
        LOGGER.info("Less than %s images found; skipping cleanup...",
                    str(IMAGES_TO_RETAIN))


if __name__ == "__main__":
    SSM_PARAM = input('Enter SSM param (eg "/myapp/image"): ')
    REPO_NAME = input('Enter ECR repo name: ')
    handler(None, None)
else:
    SSM_PARAM = os.environ['SSM_PARAM']
    REPO_NAME = os.environ['ECR_REPO_NAME']
