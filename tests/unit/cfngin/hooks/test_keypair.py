"""Tests for runway.cfngin.hooks.keypair."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, NamedTuple
from unittest import mock

import boto3
import pytest
from moto.core.decorator import mock_aws

from runway.cfngin.hooks.keypair import KeyPairInfo, ensure_keypair_exists

from ..factories import mock_context

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pytest_mock import MockerFixture

    from runway.context import CfnginContext

REGION = "us-east-1"
KEY_PAIR_NAME = "FakeKey"


class SSHKey(NamedTuple):
    """SSHKey."""

    fingerprint: str
    private_key: bytes
    public_key: bytes


@pytest.fixture(scope="module")
def ssh_key(cfngin_fixtures: Path) -> SSHKey:
    """Return an ssh key."""
    base = cfngin_fixtures / "keypair"
    return SSHKey(
        private_key=(base / "id_rsa").read_bytes(),
        public_key=(base / "id_rsa.pub").read_bytes(),
        fingerprint=(base / "fingerprint").read_text("ascii").strip(),
    )


@pytest.fixture
def context() -> CfnginContext:
    """Mock context."""
    return mock_context(namespace="fake")


@pytest.fixture(autouse=True)
def patch_ssh_key(mocker: MockerFixture, ssh_key: SSHKey) -> Iterator[None]:
    """Force moto to generate a deterministic key pair on creation."""
    mocker.patch(
        "moto.ec2.models.key_pairs.random_rsa_key_pair",
        side_effect=[
            {
                "fingerprint": ssh_key.fingerprint,
                "material": ssh_key.private_key.decode("ascii"),
                "material_public": ssh_key.public_key.decode("ascii"),
            }
        ],
    )
    with mock_aws():
        yield


@contextmanager
def mock_input(lines: tuple[str, ...] = (), isatty: bool = True) -> Iterator[mock.MagicMock]:
    """Mock input."""
    with (
        mock.patch(
            "runway.cfngin.hooks.keypair.get_raw_input", side_effect=lines
        ) as mock_get_raw_input,
        mock.patch.object(sys.stdin, "isatty", return_value=isatty),
    ):
        yield mock_get_raw_input


def assert_key_present(hook_result: KeyPairInfo, key_name: str, fingerprint: str) -> None:
    """Assert key present."""
    assert hook_result.get("key_name") == key_name
    assert hook_result.get("fingerprint") == fingerprint

    ec2 = boto3.client("ec2")
    response = ec2.describe_key_pairs(KeyNames=[key_name], DryRun=False)
    key_pairs = response.get("KeyPairs", [])

    assert len(key_pairs) == 1
    assert key_pairs[0].get("KeyName") == key_name
    assert key_pairs[0].get("KeyFingerprint") == fingerprint


def test_param_validation(context: CfnginContext) -> None:
    """Test param validation."""
    result = ensure_keypair_exists(
        context,
        keypair=KEY_PAIR_NAME,
        ssm_parameter_name="test",
        public_key_path="test",
    )
    assert result == {}


def test_keypair_exists(context: CfnginContext) -> None:
    """Test keypair exists."""
    ec2 = boto3.client("ec2")
    keypair = ec2.create_key_pair(KeyName=KEY_PAIR_NAME)

    result = ensure_keypair_exists(context, keypair=KEY_PAIR_NAME)
    expected = {
        "status": "exists",
        "key_name": KEY_PAIR_NAME,
        "fingerprint": keypair.get("KeyFingerprint"),
    }
    assert result == expected


def test_import_file(tmp_path: Path, context: CfnginContext, ssh_key: SSHKey) -> None:
    """Test import file."""
    pub_key = tmp_path / "id_rsa.pub"
    pub_key.write_bytes(ssh_key.public_key)

    result = ensure_keypair_exists(context, keypair=KEY_PAIR_NAME, public_key_path=str(pub_key))
    assert_key_present(result, KEY_PAIR_NAME, ssh_key.fingerprint)
    assert result.get("status") == "imported"


def test_import_bad_key_data(tmp_path: Path, context: CfnginContext) -> None:
    """Test import bad key data."""
    pub_key = tmp_path / "id_rsa.pub"
    pub_key.write_text("garbage")

    result = ensure_keypair_exists(context, keypair=KEY_PAIR_NAME, public_key_path=str(pub_key))
    assert result == {}


@pytest.mark.parametrize("ssm_key_id", ["my-key"])
def test_create_in_ssm(context: CfnginContext, ssh_key: SSHKey, ssm_key_id: str) -> None:
    """Test create in ssm."""
    result = ensure_keypair_exists(
        context,
        keypair=KEY_PAIR_NAME,
        ssm_parameter_name="param",
        ssm_key_id=ssm_key_id,
    )

    assert_key_present(result, KEY_PAIR_NAME, ssh_key.fingerprint)
    assert result.get("status") == "created"

    ssm = boto3.client("ssm")
    param = ssm.get_parameter(Name="param", WithDecryption=True).get("Parameter", {})
    assert param.get("Value", "").replace("\n", "") == ssh_key.private_key.decode("ascii").replace(
        os.linesep, ""
    )
    assert param.get("Type") == "SecureString"

    params = ssm.describe_parameters().get("Parameters", [])
    param_details = next(p for p in params if p.get("Name") == "param")
    assert (
        param_details.get("Description")
        == f'SSH private key for KeyPair "{KEY_PAIR_NAME}" (generated by Runway)'
    )
    assert param_details.get("KeyId") == ssm_key_id


def test_interactive_non_terminal_input(context: CfnginContext) -> None:
    """Test interactive non terminal input."""
    with mock_input(isatty=False) as _input:
        result = ensure_keypair_exists(context, keypair=KEY_PAIR_NAME)
        _input.assert_not_called()
    assert result == {}


def test_interactive_retry_cancel(context: CfnginContext) -> None:
    """Test interactive retry cancel."""
    lines = ("garbage", "cancel")
    with mock_input(lines) as _input:
        result = ensure_keypair_exists(context, keypair=KEY_PAIR_NAME)
        assert _input.call_count == 2
    assert result == {}


def test_interactive_import(tmp_path: Path, context: CfnginContext, ssh_key: SSHKey) -> None:
    """."""
    key_file = tmp_path / "id_rsa.pub"
    key_file.write_bytes(ssh_key.public_key)

    lines = ("import", str(key_file))
    with mock_input(lines):
        result = ensure_keypair_exists(context, keypair=KEY_PAIR_NAME)

    assert_key_present(result, KEY_PAIR_NAME, ssh_key.fingerprint)
    assert result.get("status") == "imported"


def test_interactive_create(tmp_path: Path, context: CfnginContext, ssh_key: SSHKey) -> None:
    """Test interactive create."""
    key_dir = tmp_path / "keys"
    key_dir.mkdir(parents=True, exist_ok=True)
    key_file = key_dir / f"{KEY_PAIR_NAME}.pem"

    lines = ("create", str(key_dir))
    with mock_input(lines):
        result = ensure_keypair_exists(context, keypair=KEY_PAIR_NAME)

    assert_key_present(result, KEY_PAIR_NAME, ssh_key.fingerprint)
    assert result.get("status") == "created"
    assert key_file.samefile(result.get("file_path", ""))
    assert key_file.read_bytes() == ssh_key.private_key


def test_interactive_create_bad_dir(tmp_path: Path, context: CfnginContext) -> None:
    """Test interactive create bad dir."""
    key_dir = tmp_path / "missing"

    lines = ("create", str(key_dir))
    with mock_input(lines):
        result = ensure_keypair_exists(context, keypair=KEY_PAIR_NAME)

    assert result == {}


def test_interactive_create_existing_file(tmp_path: Path, context: CfnginContext) -> None:
    """Test interactive create existing file."""
    key_dir = tmp_path / "keys"
    key_dir.mkdir(exist_ok=True, parents=True)
    key_file = key_dir / f"{KEY_PAIR_NAME}.pem"
    key_file.touch()

    lines = ("create", str(key_dir))
    with mock_input(lines):
        result = ensure_keypair_exists(context, keypair=KEY_PAIR_NAME)

    assert result == {}
