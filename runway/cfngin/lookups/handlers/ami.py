"""AMI lookup."""

from __future__ import annotations

import operator
import re
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import field_validator

from ....lookups.handlers.base import LookupHandler
from ....utils import BaseModel
from ...utils import read_value_from_path

if TYPE_CHECKING:

    from ....context import CfnginContext


class ArgsDataModel(BaseModel):
    """Arguments data model.

    Any other arguments specified are sent as filters to the AWS API.
    For example, ``architecture:x86_64`` will add a filter.

    """

    executable_users: list[str] | None = None
    """List of executable users."""

    owners: list[str]
    """At least one owner is required.

    Should be ``amazon``, ``self``, or an AWS account ID.

    """

    region: str | None = None
    """AWS region."""

    @field_validator("executable_users", "owners", mode="before")
    @classmethod
    def _convert_str_to_list(cls, v: list[str] | str) -> list[str]:
        """Convert str to list."""
        if isinstance(v, str):
            return v.split(",")
        return v  # cov: ignore


class ImageNotFound(Exception):
    """Image not found."""

    search_string: str

    def __init__(self, search_string: str) -> None:
        """Instantiate class."""
        self.search_string = search_string
        super().__init__(f"Unable to find ec2 image with search string: {search_string}")


class AmiLookup(LookupHandler["CfnginContext"]):
    """AMI lookup."""

    TYPE_NAME: ClassVar[str] = "ami"
    """Name that the Lookup is registered as."""

    @classmethod
    def parse_query(cls, value: str) -> tuple[str, dict[str, str]]:
        """Parse the value passed to the lookup.

        This overrides the default parsing to account for special requirements.

        Args:
            value: The raw value passed to a lookup.

        Returns:
            The lookup query and a dict of arguments

        """
        raw_value = read_value_from_path(value)
        args: dict[str, str] = {}

        if "@" in raw_value:
            args["region"], raw_value = raw_value.split("@", 1)

        # now find any other arguments that can be filters
        matches = re.findall(r"([0-9a-zA-z_-]+:[^\s$]+)", raw_value)
        for match in matches:
            k, v = match.split(":", 1)
            args[k] = v

        return args.pop("name_regex"), args

    @classmethod
    def handle(cls, value: str, context: CfnginContext, **_kwargs: Any) -> str:
        """Fetch the most recent AMI Id using a filter.

        Args:
            value: Parameter(s) given to this lookup.
            context: Context instance.

        Example:
            .. code-block:

                ${ami [<region>@]owners:self,account,amazon name_regex:serverX-[0-9]+ architecture:x64,i386}

            The above fetches the most recent AMI where owner is self
            account or amazon and the ami name matches the regex described,
            the architecture will be either x64 or i386

            You can also optionally specify the region in which to perform the
            AMI lookup.

        """
        query, raw_args = cls.parse_query(value)
        args = ArgsDataModel.model_validate(raw_args)
        ec2 = context.get_session(region=args.region).client("ec2")

        describe_args: dict[str, Any] = {
            "Filters": [
                {"Name": key, "Values": val.split(",") if val else val}
                for key, val in {
                    k: v for k, v in raw_args.items() if k not in ArgsDataModel.model_fields
                }.items()
            ],
            "Owners": args.owners,
        }
        if args.executable_users:
            describe_args["ExecutableUsers"] = args.executable_users

        result = ec2.describe_images(**describe_args)

        images = sorted(
            result.get("Images", []),
            key=operator.itemgetter("CreationDate"),
            reverse=True,
        )
        for image in images:
            # sometimes we get ARI/AKI in response - these don't have a 'Name'
            if re.match(f"^{query}$", image.get("Name", "")) and "ImageId" in image:
                return image["ImageId"]

        raise ImageNotFound(value)
