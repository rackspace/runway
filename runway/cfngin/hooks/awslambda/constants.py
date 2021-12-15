"""Constant values."""
from runway.constants import DOT_RUNWAY_DIR

AWS_SAM_BUILD_IMAGE_PREFIX = "public.ecr.aws/sam/build-"
"""Prefix for build image registries."""

BASE_WORK_DIR = DOT_RUNWAY_DIR / "awslambda"
"""Base work directory for the awslambda hooks."""

DEFAULT_IMAGE_NAME = "runway.cfngin.hooks.awslambda"
"""Default name to apply to an image when building from a Dockerfile."""

DEFAULT_IMAGE_TAG = "latest"
"""Default tag to apply to an image when building from a Dockerfile."""
