"""Parameters."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union, cast

from pydantic import validator
from typing_extensions import Literal

from ......util import BaseModel
from .utils import find_bucket_key

PathsType = Literal["local", "locallocal", "locals3", "s3", "s3local", "s3s3"]


class ParametersDataModel(BaseModel):
    """Parameters data model."""

    dest: str
    src: str
    # these need to be set after dest & src so their validators can access the value if needed
    delete: bool = False
    dir_op: bool = False
    exact_timestamps: bool = False
    follow_symlinks: bool = False
    is_move: bool = False
    only_show_errors: bool = False
    page_size: Optional[int] = None
    paths_type: PathsType = "local"  # will be overwritten
    size_only: bool = False

    @validator("paths_type", always=True, pre=True)
    @classmethod
    def _determine_paths_type(
        cls,
        v: Optional[str],  # pylint: disable=unused-argument
        values: Dict[str, Any],
    ) -> PathsType:
        """Determine paths type for the given src and dest."""
        # these have already been validated so it's "safe" to cast them
        dest = cast(str, values.get("dest"))
        src = cast(str, values.get("src"))
        src_type = "s3" if src.startswith("s3://") else "local"
        dest_type = "s3" if dest.startswith("s3://") else "local"
        return cast(PathsType, f"{src_type}{dest_type}")

    @validator("dest", "src", pre=True)
    @classmethod
    def _normalize_s3_trailing_slash(cls, v: str) -> str:
        """Add a trailing "/" if the root of an S3 bucket was provided."""
        if v.startswith("s3://"):
            _bucket, key = find_bucket_key(v[5:])
            if not key and not v.endswith("/"):
                v += "/"
        return v


class Parameters:
    """Initial error based on the parameters and arguments passed to sync."""

    def __init__(
        self, cmd: str, parameters: Union[Dict[str, Any], ParametersDataModel]
    ):
        """Instantiate class.

        Args:
            cmd: The name of the command.
            parameters: A dictionary of parameters.

        """
        self.cmd = cmd
        self.data = ParametersDataModel.parse_obj(parameters)
        if self.cmd in ["sync", "mb", "rb"]:
            self.data.dir_op = True
        if self.cmd == "mv":
            self.data.is_move = True
        else:
            self.data.is_move = False
        self._validate_path_args()

    def _validate_path_args(self) -> None:
        # If we're using a mv command, you can't copy the object onto itself.
        params = self.data
        if self.cmd == "mv" and self._same_path():
            raise ValueError(
                f"Cannot mv a file onto itself: '{params.src}' - '{params.dest}'"
            )

        # If the operation is downloading to a directory that does not exist,
        # create the directories so no warnings are thrown during the syncing
        # process.
        if params.paths_type == "s3local" and params.dir_op:
            dest_path = Path(params.dest)
            if not dest_path.exists():
                dest_path.mkdir(exist_ok=True, parents=True)

    def _same_path(self) -> bool:
        """Evaluate if the src and dest are the same path."""
        if not self.data.paths_type == "s3s3":
            return False
        if self.data.src == self.data.dest:
            return True
        return False
