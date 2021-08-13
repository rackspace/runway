"""Terraform version management."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from distutils.version import LooseVersion
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    NamedTuple,
    Optional,
    Union,
    cast,
    overload,
)
from urllib.error import URLError
from urllib.request import urlretrieve

import hcl
import hcl2
import requests
from typing_extensions import Final

from ..compat import cached_property
from ..exceptions import HclParserError
from ..utils import FileHash, get_hash_for_filename, merge_dicts
from . import EnvManager, handle_bin_download_error

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    from .._logging import RunwayLogger

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))
TF_VERSION_FILENAME = ".terraform-version"


# Branch and local variable count will go down when py2 support is dropped
def download_tf_release(  # noqa pylint: disable=too-many-locals,too-many-branches
    version: str,
    versions_dir: Path,
    command_suffix: str,
    tf_platform: Optional[str] = None,
    arch: Optional[str] = None,
) -> None:
    """Download Terraform archive and return path to it."""
    version_dir = versions_dir / version

    if arch is None:
        arch = os.getenv("TFENV_ARCH", "amd64")

    if tf_platform:
        tfver_os = tf_platform + "_" + arch
    else:
        if platform.system().startswith("Darwin"):
            tfver_os = f"darwin_{arch}"
        elif platform.system().startswith("Windows") or (
            platform.system().startswith("MINGW64")
            or (
                platform.system().startswith("MSYS_NT")
                or platform.system().startswith("CYGWIN_NT")
            )
        ):
            tfver_os = f"windows_{arch}"
        else:
            tfver_os = f"linux_{arch}"

    download_dir = tempfile.mkdtemp()
    filename = f"terraform_{version}_{tfver_os}.zip"
    shasums_name = f"terraform_{version}_SHA256SUMS"
    tf_url = "https://releases.hashicorp.com/terraform/" + version

    try:
        LOGGER.verbose("downloading Terraform from %s...", tf_url)
        for i in [filename, shasums_name]:
            urlretrieve(tf_url + "/" + i, os.path.join(download_dir, i))
    except URLError as exc:
        handle_bin_download_error(exc, "Terraform")

    tf_hash = get_hash_for_filename(filename, os.path.join(download_dir, shasums_name))
    checksum = FileHash(hashlib.sha256())
    checksum.add_file(os.path.join(download_dir, filename))
    if tf_hash != checksum.hexdigest:
        LOGGER.error(
            "downloaded Terraform %s does not match sha256 %s", filename, tf_hash
        )
        sys.exit(1)

    with zipfile.ZipFile(os.path.join(download_dir, filename)) as tf_zipfile:
        version_dir.mkdir(parents=True, exist_ok=True)
        tf_zipfile.extractall(str(version_dir))

    shutil.rmtree(download_dir)
    result = version_dir / ("terraform" + command_suffix)
    result.chmod(result.stat().st_mode | 0o0111)  # ensure it is executable


def get_available_tf_versions(include_prerelease: bool = False) -> List[str]:
    """Return available Terraform versions."""
    tf_releases = json.loads(
        requests.get("https://releases.hashicorp.com/index.json").text
    )["terraform"]
    tf_versions = sorted(
        [k for k, _v in tf_releases["versions"].items()],  # descending
        key=LooseVersion,
        reverse=True,
    )
    if include_prerelease:
        return [i for i in tf_versions if i]
    return [i for i in tf_versions if i and "-" not in i]


def get_latest_tf_version(include_prerelease: bool = False) -> str:
    """Return latest Terraform version."""
    return get_available_tf_versions(include_prerelease)[0]


def load_terraform_module(parser: ModuleType, path: Path) -> Dict[str, Any]:
    """Load all Terraform files in a module into one dict.

    Args:
        parser (Union[hcl, hcl2]): Parser to use when loading files.
        path: Terraform module path. All Terraform files in the
            path will be loaded.

    """
    result: Dict[str, Any] = {}
    LOGGER.debug("using %s parser to load module: %s", parser.__name__.upper(), path)
    for tf_file in path.glob("*.tf"):
        try:
            tf_config = parser.loads(tf_file.read_text())  # type: ignore
            result = merge_dicts(result, cast(Dict[str, Any], tf_config))
        except Exception as exc:
            raise HclParserError(exc, tf_file, parser) from None
    return result


class VersionTuple(NamedTuple):
    """Terraform version tuple.

    Attributes:
        major: Major release version number.
        minor: Minor release version number.
        patch: Patch release version number.
        prerelease: Prerelease identifier (e.g. ``beta2``).

    """

    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    prerelease_number: Optional[int] = None

    def __str__(self) -> str:
        """Format as string."""
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            result += f"-{self.prerelease}"
        if self.prerelease_number:
            result += str(self.prerelease_number)
        return result


class TFEnvManager(EnvManager):
    """Terraform version management.

    Designed to be compatible with https://github.com/tfutils/tfenv.

    """

    VERSION_REGEX: Final[str] = (
        r"^(?P<major>[0-9]*)\.(?P<minor>[0-9]*)\.(?P<patch>[0-9]*)"
        r"(\-(?P<prerelease>alpha|beta|oci|rc)(?P<prerelease_number>[0-9]*)?)?"
    )
    VERSION_OUTPUT_REGEX: Final[
        str
    ] = r"^Terraform v(?P<version>[0-9]*\.[0-9]*\.[0-9]*)(?P<suffix>-.*)?"

    def __init__(self, path: Optional[Path] = None) -> None:
        """Initialize class."""
        super().__init__("terraform", "tfenv", path)

    @cached_property
    def backend(self) -> Dict[str, Any]:
        """Backend config of the Terraform module."""
        # Terraform can only have one backend configured; this formats the
        # data to make it easier to work with
        return [
            {"type": k, "config": v}
            for k, v in self.terraform_block.get(
                "backend", {None: cast(Dict[str, str], {})}
            ).items()
        ][0]

    @cached_property
    def terraform_block(self) -> Dict[str, Any]:
        """Collect Terraform configuration blocks from a Terraform module."""

        @overload
        def _flatten_lists(data: Dict[str, Any]) -> Dict[str, Any]:
            ...

        @overload
        def _flatten_lists(data: List[Any]) -> List[Any]:
            ...

        @overload
        def _flatten_lists(data: str) -> str:
            ...

        def _flatten_lists(
            data: Union[Dict[str, Any], List[Any], Any]
        ) -> Union[Dict[str, Any], Any]:
            """Flatten HCL2 list attributes until its fixed.

            python-hcl2 incorrectly turns all attributes into lists so we need
            to flatten them so they are more similar to HCL.

            https://github.com/amplify-education/python-hcl2/issues/6

            Args:
                data: Dict with lists to flatten.

            """
            if not isinstance(data, dict):
                return data
            copy_data = cast(Dict[str, Any], data.copy())
            for attr, val in copy_data.items():
                if isinstance(val, list):
                    if len(cast(List[Any], val)) == 1:
                        # pull single values out of lists
                        data[attr] = _flatten_lists(cast(Any, val[0]))
                    else:
                        data[attr] = [_flatten_lists(v) for v in cast(List[Any], val)]
                elif isinstance(val, dict):
                    data[attr] = _flatten_lists(cast(Dict[str, Any], val))
            return data

        try:
            result: Union[Dict[str, Any], List[Dict[str, Any]]] = load_terraform_module(
                hcl2, self.path
            ).get("terraform", cast(Dict[str, Any], {}))
        except HclParserError as exc:
            LOGGER.warning(exc)
            LOGGER.warning("failed to parse as HCL2; trying HCL...")
            try:
                result = load_terraform_module(hcl, self.path).get(
                    "terraform", cast(Dict[str, Any], {})
                )
            except HclParserError as exc:
                LOGGER.warning(exc)
                # return an empty dict if we can't parse HCL
                # let Terraform decide if it's actually valid
                result = {}

        # python-hcl2 turns all blocks into lists in v0.3.0. this flattens it.
        if isinstance(result, list):
            return _flatten_lists({k: v for i in result for k, v in i.items()})
        return _flatten_lists(result)

    @cached_property
    def version(self) -> Optional[VersionTuple]:
        """Terraform version."""
        version_requested = self.current_version or self.get_version_from_file()

        if not version_requested:
            return None

        if re.match(r"^min-required$", version_requested):
            LOGGER.debug("tfenv: detecting minimal required version")
            version_requested = self.get_min_required()

        if re.match(r"^latest:.*$", version_requested):
            regex = re.search(r"latest:(.*)", version_requested).group(  # type: ignore
                1
            )
            include_prerelease_versions = False
        elif re.match(r"^latest$", version_requested):
            regex = r"^[0-9]+\.[0-9]+\.[0-9]+$"
            include_prerelease_versions = False
        else:
            regex = f"^{version_requested}$"
            include_prerelease_versions = True
            # Return early (i.e before reaching out to the internet) if the
            # matching version is already installed
            if (self.versions_dir / version_requested).is_dir():
                self.current_version = version_requested
                return self.parse_version_string(self.current_version)

        try:
            version = next(
                i
                for i in get_available_tf_versions(include_prerelease_versions)
                if re.match(regex, i)
            )
        except StopIteration:
            LOGGER.error("unable to find a Terraform version matching regex: %s", regex)
            sys.exit(1)
        self.current_version = version
        return self.parse_version_string(self.current_version)

    @cached_property
    def version_file(self) -> Optional[Path]:
        """Find and return a ".terraform-version" file if one is present.

        Returns:
            Path to the Terraform version file.

        """
        for path in [self.path, self.path.parent]:
            test_path = path / TF_VERSION_FILENAME
            if test_path.is_file():
                LOGGER.debug("using version file: %s", test_path)
                return test_path
        return None

    def get_min_required(self) -> str:
        """Get the defined minimum required version of Terraform.

        Returns:
            The minimum required version as defined in the module.

        """
        version = self.terraform_block.get("required_version")

        if version:
            if re.match(r"^!=.+", version):
                LOGGER.error(
                    "min required Terraform version is a negation (%s) "
                    "- unable to determine required version",
                    version,
                )
                sys.exit(1)
            else:
                version = re.search(r"[0-9]*\.[0-9]*(?:\.[0-9]*)?", version)
                if version:
                    LOGGER.debug("detected minimum Terraform version is %s", version)
                    return version.group(0)
        LOGGER.error(
            "Terraform version specified as min-required, but unable to "
            "find a specified version requirement in this module's tf files"
        )
        sys.exit(1)

    def get_version_from_file(self, file_path: Optional[Path] = None) -> Optional[str]:
        """Get Terraform version from a file.

        Args:
            file_path: Path to file that will be read.

        """
        file_path = file_path or self.version_file
        if file_path and file_path.is_file():
            return file_path.read_text().strip()
        LOGGER.debug("file path not provided and version file could not be found")
        return None

    def install(self, version_requested: Optional[str] = None) -> str:
        """Ensure Terraform is available."""
        if version_requested:
            self.set_version(version_requested)

        if not self.version:
            raise ValueError(
                f"version not provided and unable to find a {TF_VERSION_FILENAME} file"
            )

        # Now that a version has been selected, skip downloading if it's
        # already been downloaded
        if (self.versions_dir / str(self.version)).is_dir():
            LOGGER.verbose(
                "Terraform version %s already installed; using it...", self.version
            )
            return str(self.bin)

        LOGGER.info("downloading and using Terraform version %s ...", self.version)
        download_tf_release(str(self.version), self.versions_dir, self.command_suffix)
        LOGGER.verbose("downloaded Terraform %s successfully", self.version)
        return str(self.bin)

    def list_installed(self) -> Generator[Path, None, None]:
        """List installed versions of Terraform.

        Only lists versions of Terraform that have been installed by an instance
        if this class or by tfenv.

        """
        LOGGER.verbose("checking %s for Terraform versions...", self.versions_dir)
        return self.versions_dir.rglob("*.*.*")

    def set_version(self, version: str) -> None:
        """Set current version.

        Clears cached values as needed.

        Args:
            version: Version string. Must be in the format of
                ``<major>.<minor>.<patch>`` with an optional ``-<prerelease>``.

        """
        if self.current_version == version:
            return
        self.current_version = version
        try:
            del self.version
        except Exception:  # pylint: disable=broad-except
            pass

    @classmethod
    def get_version_from_executable(
        cls,
        bin_path: Union[Path, str],
        *,
        cwd: Optional[Union[Path, str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Optional[VersionTuple]:
        """Get Terraform version from an executable.

        Args:
            bin_path: Path to the Terraform binary to retrieve the version from.
            cwd: Current working directory to use when calling the executable.
            env: Environment variable overrides.

        """
        output = subprocess.check_output(
            [str(bin_path), "-version"], cwd=cwd, env=env
        ).decode()
        match = re.search(cls.VERSION_OUTPUT_REGEX, output)
        if not match:
            return None
        return cls.parse_version_string(match.group("version"))

    @classmethod
    def parse_version_string(cls, version: str) -> VersionTuple:
        """Parse version string into a :class:`VersionTuple`.

        Args:
            version: Version string to parse. Must be in the format of
                ``<major>.<minor>.<patch>`` with an optional ``-<prerelease>``.

        """
        match = re.search(cls.VERSION_REGEX, version)
        if not match:
            raise ValueError(
                f"provided version doesn't conform to regex: {cls.VERSION_REGEX}"
            )
        return VersionTuple(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease") or None,
            prerelease_number=int(match.group("prerelease_number") or 0) or None,
        )
