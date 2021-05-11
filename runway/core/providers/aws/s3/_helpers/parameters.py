"""Parameters."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

from pydantic import validator
from typing_extensions import Literal

from ......utils import BaseModel
from .utils import find_bucket_key

PathsType = Literal["local", "locallocal", "locals3", "s3", "s3local", "s3s3"]


class ParametersDataModel(BaseModel):
    """Parameters data model.

    Attributes:
        dest: File/object destination.
        src: File/object source.
        content_type: Explicitly provided content type.
        delete: Whether or not to delete files at the destination that are
            missing from the source location.
        dir_op: If the source location is a directory.
        dryrun: Whether this is a dry run.
        exact_timestamps: Use exact time stamp when comparing files/objects
            during sync.
        exclude: List of patterns for files/objects to exclude.
        expected_size: Expected size of transfer.
        follow_symlinks: Whether or not to follow symlinks.
        force_glacier_transfer: Force transfer even if glacier.
        guess_mime_type: Whether or not to guess content type.
        ignore_glacier_warnings: Don't show glacier warnings.
        include: List of patterns for files/objects to explicitly include.
        is_move: Whether or not the action is move.
        is_stream: Source or destination is a stream.
        no_progress: Whether to not show progress.
        only_show_errors: Whether or not to only show errors while running.
        page_size: Number of objects to list per call.
        quiet: Don't output anything.
        paths_type: Concatinated path types for source and destination.
        size_only: When comparing files/objects, only consider size.
        storage_class: S3 storage class.

    """

    dest: str
    src: str
    # these need to be set after dest & src so their validators can access the value if needed
    content_type: Optional[str] = None
    delete: bool = False
    dir_op: bool = False
    dryrun: bool = False
    exact_timestamps: bool = False
    exclude: List[str] = []
    expected_size: Optional[int] = None
    follow_symlinks: bool = False
    force_glacier_transfer: bool = False
    guess_mime_type: bool = True
    ignore_glacier_warnings: bool = False
    include: List[str] = []
    is_move: bool = False
    is_stream: bool = False
    no_progress: bool = False
    only_show_errors: bool = False
    page_size: Optional[int] = None
    paths_type: PathsType = "local"  # will be overwritten
    quiet: bool = False
    size_only: bool = False
    sse_c: Optional[str] = None
    sse_c_key: Optional[str] = None
    storage_class: Optional[str] = None

    @validator("paths_type", always=True, pre=True)
    @classmethod
    def _determine_paths_type(
        cls,
        v: Optional[str],  # pylint: disable=unused-argument
        values: Dict[str, Any],
    ) -> PathsType:
        """Determine paths type for the given src and dest."""
        # these have already been validated so it's "safe" to cast them
        dest = cast(str, values.get("dest", ""))
        src = cast(str, values.get("src", ""))
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
        self, action: str, parameters: Union[Dict[str, Any], ParametersDataModel]
    ):
        """Instantiate class.

        Args:
            action: The name of the action.
            parameters: A dictionary of parameters.

        """
        self.action = action
        self.data = ParametersDataModel.parse_obj(parameters)
        if self.action in ["sync", "mb", "rb"]:
            self.data.dir_op = True
        if self.action == "mv":
            self.data.is_move = True
        else:
            self.data.is_move = False
        self._validate_path_args()

    def _validate_path_args(self) -> None:
        # If we're using a mv command, you can't copy the object onto itself.
        if self.action == "mv" and self._same_path():
            raise ValueError(
                f"Cannot mv a file onto itself: '{self.data.src}' - '{self.data.dest}'"
            )

        # If the operation is downloading to a directory that does not exist,
        # create the directories so no warnings are thrown during the syncing
        # process.
        if self.data.paths_type == "s3local" and self.data.dir_op:
            dest_path = Path(self.data.dest)
            if not dest_path.exists():
                dest_path.mkdir(exist_ok=True, parents=True)

    def _same_path(self) -> bool:
        """Evaluate if the src and dest are the same path."""
        if not self.data.paths_type == "s3s3":
            return False
        if self.data.src == self.data.dest:
            return True
        return False
