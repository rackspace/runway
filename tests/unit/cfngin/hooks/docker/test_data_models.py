"""Test runway.cfngin.hooks.docker.data_models."""
# pylint: disable=no-self-use,protected-access,redefined-outer-name
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pytest
from docker.models.images import Image
from mock import MagicMock

from runway.cfngin.hooks.docker.data_models import (
    BaseModel,
    DockerImage,
    ElasticContainerRegistry,
    ElasticContainerRegistryRepository,
)
from runway.util import MutableMap

if TYPE_CHECKING:
    import sys  # pylint: disable=E

    from pytest_mock import MockerFixture

    from ....factories import MockCFNginContext

    if sys.version_info.major > 2:
        from pathlib import Path  # pylint: disable=E
    else:
        from pathlib2 import Path  # type: ignore pylint: disable=E

MODULE = "runway.cfngin.hooks.docker.data_models"
MOCK_IMAGE_REPO = "dkr.test.com/image"
MOCK_IMAGE_PROPS = {
    "attrs": {"RepoTags": ["dkr.test.com/image:latest", "dkr.test.com/image:oldest"]},
    "id": "acb123",
    "short_id": "sha256:abc",
    "tags": ["dkr.test.com/image:latest", "dkr.test.com/image:oldest"],
}


@pytest.fixture(scope="function")
def mock_image():  # type: () -> MagicMock
    """Return a mock docker.models.images.Image."""
    return MagicMock(spec=Image, **MOCK_IMAGE_PROPS)


class SampleModel(BaseModel):
    """Class to test the BaseModel."""

    def __init__(self, **kwargs):
        """Instantiate class."""
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestBaseModel(object):
    """Test runway.cfngin.hooks.docker._data_models.BaseModel."""

    def test_dict(self):  # type: () -> None
        """Test dict."""
        obj = SampleModel(key="val", _key="val")
        assert obj.dict() == {"key": "val"}

    def test_find(self):  # type: () -> None
        """Test find."""
        obj = SampleModel(key="val")
        assert obj.find("key") == "val"
        assert obj.find("missing") is None
        assert obj.find("missing", "default") == "default"

    def test_find_nested(self):  # type: () -> None
        """Test find nested value."""
        assert (
            SampleModel(lang=SampleModel(python="found")).find("lang.python") == "found"
        )
        assert (
            SampleModel(lang=SampleModel(**{"python3.8": "found"})).find(
                "lang.python3.8"
            )
            == "found"
        )
        assert (
            SampleModel(lang=SampleModel(**{"python3.8": "found"})).find(
                "lang.python3.9", "not found"
            )
            == "not found"
        )

    def test_find_nested_attr_key_error(self):  # type: () -> None
        """Test find nested AttributeError/KeyError."""
        assert (
            SampleModel(lang={"python": {"3": "found"}}).find(
                "lang.python.3", "default"
            )
            == "default"
        )

    def test_get(self):  # type: () -> None
        """Test get."""
        obj = SampleModel(key="val")
        assert obj.get("key") == obj["key"]
        assert obj.get("missing") is None
        assert obj.get("missing", "default") == "default"

    @pytest.mark.parametrize("provided", [{"key": "val"}, SampleModel(key="val")])
    def test_parse_obj(self, provided):  # type: (Any) -> None
        """Test parse_obj."""
        obj = SampleModel.parse_obj(provided)
        provided["context"] = None
        assert isinstance(obj, SampleModel)
        assert obj == provided

    def test_parse_obj_type_error(self):  # type: () -> None
        """Test parse_obj raise TypeError."""
        with pytest.raises(TypeError):
            SampleModel.parse_obj(["something"])

    @pytest.mark.parametrize(
        "provided, expected",
        [(True, True), (False, False), (None, False), ("", False), ("false", True)],
    )
    def test_validate_bool(self, provided, expected):  # type: (Any, bool) -> None
        """Test _validate_bool."""
        assert BaseModel._validate_bool(provided) is expected

    @pytest.mark.parametrize(
        "provided, optional, required, expected",
        [
            (None, False, False, {}),
            (None, True, False, None),
            ({}, False, False, {}),
            ({}, True, False, {}),
            ({"key": "val"}, False, False, {"key": "val"}),
            ({"key": "val"}, True, False, {"key": "val"}),
            ({"key": "val"}, False, True, {"key": "val"}),
            ({"key": "val"}, True, True, {"key": "val"}),
            (SampleModel(key="val"), False, False, {"key": "val"}),
        ],
    )
    def test_validate_dict(self, provided, optional, required, expected):
        # type: (Any, bool, bool, Optional[Dict[str, Any]]) -> None
        """Test _validate_dict."""
        assert (
            BaseModel._validate_dict(provided, optional=optional, required=required)
            == expected
        )

    def test_validate_dict_value_error(self):  # type: () -> None
        """Test _validate_dict raise ValueError."""
        with pytest.raises(ValueError):
            BaseModel._validate_dict(["something"])
        with pytest.raises(ValueError):
            BaseModel._validate_dict(None, required=True)
        with pytest.raises(ValueError):
            BaseModel._validate_dict({}, required=True)

    @pytest.mark.parametrize(
        "provided, optional, required, expected",
        [
            (None, False, False, 0),
            (None, True, False, None),
            (0, False, False, 0),
            (0, True, False, 0),
            (0, False, True, 0),
            (0, True, True, 0),
            (13, False, False, 13),
            ("13", False, False, 13),
        ],
    )
    def test_validate_int(self, provided, optional, required, expected):
        # type: (Any, bool, bool, Optional[int]) -> None
        """Test _validate_int."""
        assert (
            BaseModel._validate_int(provided, optional=optional, required=required)
            == expected
        )

    def test_validate_int_value_error(self):  # type: () -> None
        """Test _validate_int raise ValueError."""
        with pytest.raises(ValueError):
            BaseModel._validate_int(None, required=True)
        with pytest.raises(ValueError):
            BaseModel._validate_int("something")

    @pytest.mark.parametrize(
        "provided, optional, required, expected",
        [
            (None, False, False, []),
            (None, True, False, None),
            ([], False, False, []),
            ([], True, False, []),
            (["something"], False, True, ["something"]),
            (["something"], True, True, ["something"]),
            ({"something"}, False, False, ["something"]),
            (("something",), False, False, ["something"]),
            ("abc", False, False, ["a", "b", "c"]),
        ],
    )
    def test_validate_list_str(self, provided, optional, required, expected):
        # type: (Any, bool, bool, Optional[List[str]]) -> None
        """Test _validate_list_str."""
        assert (
            BaseModel._validate_list_str(provided, optional=optional, required=required)
            == expected
        )

    def test_validate_list_str_type_error(self):  # type: () -> None
        """Test _validate_list_str raise TypeError."""
        with pytest.raises(TypeError):
            BaseModel._validate_list_str(["something", None])
        with pytest.raises(TypeError):
            BaseModel._validate_list_str(1)

    def test_validate_list_str_value_error(self):  # type: () -> None
        """Test _validate_list_str raise ValueError."""
        with pytest.raises(ValueError):
            BaseModel._validate_list_str(None, required=True)

    def test_validate_path(self, tmp_path):  # type: ("Path") -> None
        """Test validate_path."""
        assert BaseModel._validate_path(str(tmp_path)) == tmp_path
        assert BaseModel._validate_path(str(tmp_path), must_exist=True) == tmp_path
        assert BaseModel._validate_path(tmp_path) == tmp_path
        assert BaseModel._validate_path(tmp_path, must_exist=True) == tmp_path

    def test_validate_path_type_error(self):  # type: () -> None
        """Test _validate_path raise TypeError."""
        with pytest.raises(TypeError):
            BaseModel._validate_path(13)

    def test_validate_path_value_error(self, tmp_path):  # type: ("Path") -> None
        """Test _validate_path raise ValueError."""
        with pytest.raises(ValueError):
            BaseModel._validate_path(tmp_path / "missing", must_exist=True)

    @pytest.mark.parametrize(
        "provided, optional, required, expected",
        [
            (None, False, False, "None"),
            (None, True, False, None),
            ("", False, False, ""),
            ("", True, False, ""),
            ("something", False, False, "something"),
            ("something", True, False, "something"),
            ("something", False, True, "something"),
            ("something", True, True, "something"),
            (0, False, False, "0"),
            (0, True, False, None),
            (1, False, False, "1"),
        ],
    )
    def test_validate_str(self, provided, optional, required, expected):
        # type: (Any, bool, bool, Optional[str]) -> None
        """Test _validate_str."""
        assert (
            BaseModel._validate_str(provided, optional=optional, required=required)
            == expected
        )

    @pytest.mark.parametrize(
        "provided", [{"key": "val"}, ["something"], {"something"}, ("something",)]
    )
    def test_validate_str_type_error(self, provided):
        # type: (Any) -> None
        """Test _validate_str raise TypeError."""
        with pytest.raises(TypeError):
            BaseModel._validate_str(provided)

    def test_validate_str_value_error(self):
        # type: () -> None
        """Test _validate_str raise ValueError."""
        with pytest.raises(ValueError):
            BaseModel._validate_str(None, required=True)
        with pytest.raises(ValueError):
            BaseModel._validate_str("", required=True)


class TestDockerImage(object):
    """Test runway.cfngin.hooks.docker.data_models.DockerImage."""

    def test_id(self, mock_image):  # type: (MagicMock) -> None
        """Test id."""
        obj = DockerImage(image=mock_image)
        assert obj.id == MOCK_IMAGE_PROPS["id"]
        obj.id = "new-id"
        assert obj.id == "new-id"

    def test_repo(self, mock_image):  # type: (MagicMock) -> None
        """Test repo."""
        obj = DockerImage(image=mock_image)
        assert obj.repo == MOCK_IMAGE_REPO
        obj.repo = "new-repo"
        assert obj.repo == "new-repo"

    def test_sort_id(self, mock_image):  # type: (MagicMock) -> None
        """Test short_id."""
        obj = DockerImage(image=mock_image)
        assert obj.short_id == MOCK_IMAGE_PROPS["short_id"]
        obj.short_id = "new-id"
        assert obj.short_id == "new-id"

    def test_tags(self, mock_image):  # type: (MagicMock) -> None
        """Test tags."""
        assert DockerImage(image=mock_image).tags == ["latest", "oldest"]

    def test_uri(self, mock_image):  # type: (MagicMock) -> None
        """Test URI."""
        assert DockerImage(image=mock_image).uri == MutableMap(
            latest=MOCK_IMAGE_REPO + ":latest", oldest=MOCK_IMAGE_REPO + ":oldest"
        )


class TestElasticContainerRegistry(object):
    """Test runway.cfngin.hooks.docker._data_models.ElasticContainerRegistry."""

    def test_fqn_private(self):  # type: () -> None
        """Test fqn private."""
        obj = ElasticContainerRegistry(
            account_id="123456789012", aws_region="us-east-1"
        )
        assert obj.fqn == "123456789012.dkr.ecr.us-east-1.amazonaws.com/"

    def test_fqn_public(self):  # type: () -> None
        """Test fqn public."""
        obj = ElasticContainerRegistry(alias="test")
        assert obj.fqn == "public.ecr.aws/test/"

    def test_init_default(self, cfngin_context):  # type: ("MockCFNginContext") -> None
        """Test init default values."""
        account_id = "123456789012"
        sts_stubber = cfngin_context.add_stubber("sts")
        sts_stubber.add_response(
            "get_caller_identity",
            {
                "UserId": "str",
                "Account": account_id,
                "Arn": "arn:aws:iam:::user/test-user",
            },
        )

        with sts_stubber:
            obj = ElasticContainerRegistry(context=cfngin_context)
        sts_stubber.assert_no_pending_responses()
        assert obj.account_id == account_id
        assert obj.alias is None
        assert obj.region == cfngin_context.region
        assert not obj.public

    def test_init_no_context(self):  # type: () -> None
        """Test init with no context."""
        with pytest.raises(ValueError) as excinfo:
            ElasticContainerRegistry()
        assert str(excinfo.value) == "context is required to resolve values"

    def test_init_private(self):  # type: () -> None
        """Test init private."""
        account_id = "123456789012"
        region = "us-east-1"
        obj = ElasticContainerRegistry(account_id=account_id, aws_region=region)
        assert obj.account_id == account_id
        assert obj.alias is None
        assert obj.region == region
        assert not obj.public

    def test_init_public(self):  # type: () -> None
        """Test init public."""
        obj = ElasticContainerRegistry(alias="test")
        assert obj.account_id is None
        assert obj.alias == "test"
        assert obj.region is None
        assert obj.public


class TestElasticContainerRegistryRepository(object):
    """Test runway.cfngin.hooks.docker._data_models.ElasticContainerRegistryRepository."""

    def test_fqn_private(self, cfngin_context, mocker):
        # type: ("MockCFNginContext", "MockerFixture") -> None
        """Test init private."""
        account_id = "123456789012"
        region = "us-east-1"
        mock_registry = mocker.patch(
            MODULE + ".ElasticContainerRegistry", MagicMock(fqn="repository/")
        )
        mock_registry.return_value = mock_registry
        obj = ElasticContainerRegistryRepository(
            repo_name="something",
            account_id=account_id,
            aws_region=region,
            context=cfngin_context,
        )
        assert obj.fqn == "repository/something"
        mock_registry.assert_called_once_with(
            account_id=account_id, alias=None, aws_region=region, context=cfngin_context
        )

    def test_fqn_public(self, cfngin_context, mocker):
        # type: ("MockCFNginContext", "MockerFixture") -> None
        """Test init public."""
        mock_registry = mocker.patch(
            MODULE + ".ElasticContainerRegistry", MagicMock(fqn="repository/")
        )
        mock_registry.return_value = mock_registry
        obj = ElasticContainerRegistryRepository(
            repo_name="something", registry_alias="test", context=cfngin_context,
        )
        assert obj.fqn == "repository/something"
        mock_registry.assert_called_once_with(
            account_id=None, alias="test", aws_region=None, context=cfngin_context
        )

    def test_init_default(self, mocker):  # type: ("MockerFixture") -> None
        """Test init default values."""
        mock_registry = mocker.patch(MODULE + ".ElasticContainerRegistry")
        obj = ElasticContainerRegistryRepository(repo_name="something")
        assert obj.name == "something"
        assert obj.registry == mock_registry.return_value
        mock_registry.assert_called_once_with(
            account_id=None, alias=None, aws_region=None, context=None
        )
