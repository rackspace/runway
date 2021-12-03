"""Constant values."""
from runway.constants import DOT_RUNWAY_DIR

AWS_SAM_BUILD_IMAGE_PREFIX = "public.ecr.aws/sam/build-"
"""Prefix for build image registries."""

BASE_WORK_DIR = DOT_RUNWAY_DIR / "awslambda"
"""Base work directory for the awslambda hooks."""
