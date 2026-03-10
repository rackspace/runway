"""Changeset output utilities for CI/CD integration."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__.replace("._", ".")))


def output_changesets(
    changesets: dict[str, str],
    output_format: str = "text",
) -> None:
    """Output changeset information.

    Args:
        changesets: Dictionary mapping stack FQN to changeset ARN/ID.
        output_format: Output format - "text" for human-readable, "json" for CI/CD.

    """
    if output_format == "json":
        # Always output valid JSON for CI/CD parsing, even if empty
        output = {
            "changesets": [
                {"stack": stack_fqn, "changeset_id": cs_id}
                for stack_fqn, cs_id in changesets.items()
            ]
        }
        print(json.dumps(output, indent=2))  # noqa: T201
        if not changesets:
            LOGGER.info("No changesets created (no changes detected)")
        return

    # Text output format
    if not changesets:
        LOGGER.info("No changesets created (no changes detected)")
        return

    LOGGER.info("Retained changesets for later execution:")
    for stack_fqn, changeset_id in changesets.items():
        LOGGER.info("  %s: %s", stack_fqn, changeset_id)
    LOGGER.info("")
    LOGGER.info("To execute these changesets, run:")
    LOGGER.info("  runway deploy --execute-changesets <changesets.json>")
    LOGGER.info("")
    LOGGER.info("To generate the JSON file, re-run with --output json:")
    LOGGER.info("  runway plan --create-changeset --output json > changesets.json")
