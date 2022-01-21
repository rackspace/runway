"""Test runway.core.components._module_path."""
# pylint: disable=no-self-use
# pyright: basic
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import pytest
from mock import MagicMock
from typing_extensions import TypedDict

from runway.config.components.runway import RunwayModuleDefinition
from runway.config.models.runway import RunwayModuleDefinitionModel
from runway.core.components._module_path import ModulePath

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from runway.core.components import DeployEnvironment

MODULE = "runway.core.components._module_path"


TypeDefTestDefinitionExpected = TypedDict(
    "TypeDefTestDefinitionExpected",
    arguments=Dict[str, str],
    location=str,
    source=str,
    uri=str,
)
TypeDefTestDefinition = TypedDict(
    "TypeDefTestDefinition",
    definition=Optional[Union[Path, str]],
    expected=TypeDefTestDefinitionExpected,
)

TESTS: List[TypeDefTestDefinition] = [
    {
        "definition": "git::git://github.com/onicagroup/foo/bar.git",
        "expected": {
            "location": "./",
            "arguments": {},
            "source": "git",
            "uri": "git://github.com/onicagroup/foo/bar.git",
        },
    },
    {
        "definition": "git::git://github.com/onicagroup/foo/bar.git//foo/bar",
        "expected": {
            "location": "foo/bar",
            "arguments": {},
            "source": "git",
            "uri": "git://github.com/onicagroup/foo/bar.git",
        },
    },
    {
        "definition": "git::git://github.com/onicagroup/foo/bar.git?branch=foo",
        "expected": {
            "location": "./",
            "arguments": {"branch": "foo"},
            "source": "git",
            "uri": "git://github.com/onicagroup/foo/bar.git",
        },
    },
    {
        "definition": "git::git://github.com/onicagroup/foo/bar.git?branch=foo&bar=baz",
        "expected": {
            "location": "./",
            "arguments": {"branch": "foo", "bar": "baz"},
            "source": "git",
            "uri": "git://github.com/onicagroup/foo/bar.git",
        },
    },
    {
        "definition": "git::git://github.com/onicagroup/foo/bar.git//src/foo/bar?branch=foo",
        "expected": {
            "location": "src/foo/bar",
            "arguments": {"branch": "foo"},
            "source": "git",
            "uri": "git://github.com/onicagroup/foo/bar.git",
        },
    },
    {
        "definition": "git::git://github.com/onicagroup/foo/bar.git//src/foo/bar?branch=foo&bar=baz",  # noqa
        "expected": {
            "location": "src/foo/bar",
            "arguments": {"branch": "foo", "bar": "baz"},
            "source": "git",
            "uri": "git://github.com/onicagroup/foo/bar.git",
        },
    },
    {
        "definition": Path.cwd(),
        "expected": {"location": "./", "arguments": {}, "source": "local", "uri": ""},
    },
    {
        "definition": None,
        "expected": {"location": "./", "arguments": {}, "source": "local", "uri": ""},
    },
    {
        "definition": "/Users/kyle/repos/runway/.demo",
        "expected": {
            "location": "/Users/kyle/repos/runway/.demo",
            "arguments": {},
            "source": "local",
            "uri": "",
        },
    },
    {
        "definition": "local:://example/path",
        "expected": {
            "location": "example/path",
            "arguments": {},
            "source": "local",
            "uri": "",
        },
    },
    {
        "definition": "/example/path",
        "expected": {
            "location": "/example/path",
            "arguments": {},
            "source": "local",
            "uri": "",
        },
    },
    {
        "definition": "./example/path",
        "expected": {
            "location": "./example/path",
            "arguments": {},
            "source": "local",
            "uri": "",
        },
    },
    {
        "definition": "//example/path",
        "expected": {
            "location": "//example/path",
            "arguments": {},
            "source": "local",
            "uri": "",
        },
    },
    {
        "definition": "sampleapp.cfn",
        "expected": {
            "location": "sampleapp.cfn",
            "arguments": {},
            "source": "local",
            "uri": "",
        },
    },
]


class TestModulePath:
    """Test runway.core.components._module_path.ModulePath."""

    @pytest.mark.parametrize("test", deepcopy(TESTS))
    def test_arguments(
        self,
        deploy_environment: DeployEnvironment,
        test: TypeDefTestDefinition,
        tmp_path: Path,
    ) -> None:
        """Test arguments."""
        assert (
            ModulePath(
                test["definition"],
                cache_dir=tmp_path,
                deploy_environment=deploy_environment,
            ).arguments
            == test["expected"]["arguments"]
        )

    @pytest.mark.parametrize("test", deepcopy(TESTS))
    def test_location(
        self,
        deploy_environment: DeployEnvironment,
        test: TypeDefTestDefinition,
        tmp_path: Path,
    ) -> None:
        """Test location."""
        assert (
            ModulePath(
                test["definition"],
                cache_dir=tmp_path,
                deploy_environment=deploy_environment,
            ).location
            == test["expected"]["location"]
        )

    @pytest.mark.parametrize("test", deepcopy(TESTS))
    def test_metadata(
        self,
        deploy_environment: DeployEnvironment,
        test: TypeDefTestDefinition,
        tmp_path: Path,
    ) -> None:
        """Test metadata."""
        assert ModulePath(
            test["definition"],
            cache_dir=tmp_path,
            deploy_environment=deploy_environment,
        ).metadata == {
            "arguments": test["expected"]["arguments"],
            "cache_dir": tmp_path,
            "location": test["expected"]["location"],
            "source": test["expected"]["source"],
            "uri": test["expected"]["uri"],
        }

    def test_module_root_not_implimented(self, tmp_path: Path) -> None:
        """Test module_root NotImplimentedError."""
        with pytest.raises(NotImplementedError):
            assert not ModulePath("invalid::something", cache_dir=tmp_path).module_root

    @pytest.mark.parametrize("test", deepcopy(TESTS))
    def test_module_root(
        self,
        deploy_environment: DeployEnvironment,
        mocker: MockerFixture,
        test: TypeDefTestDefinition,
        tmp_path: Path,
    ) -> None:
        """Test module_root."""
        mocker.patch.object(ModulePath, "REMOTE_SOURCE_HANDLERS", {"git": MagicMock()})
        obj = ModulePath(
            test["definition"],
            cache_dir=tmp_path,
            deploy_environment=deploy_environment,
        )
        if isinstance(test["definition"], (type(None), Path)):
            assert obj.module_root == test["definition"] or Path.cwd()
        elif test["expected"]["source"] == "local":
            assert (
                obj.module_root
                == deploy_environment.root_dir / test["expected"]["location"]
            )
        else:
            assert (
                obj.module_root
                == ModulePath.REMOTE_SOURCE_HANDLERS[
                    obj.source
                ].return_value.fetch.return_value  # type: ignore
            )
            ModulePath.REMOTE_SOURCE_HANDLERS[obj.source].assert_called_once_with(  # type: ignore
                **obj.metadata
            )
            ModulePath.REMOTE_SOURCE_HANDLERS[
                obj.source
            ].return_value.fetch.assert_called_once_with()  # type: ignore

    @pytest.mark.parametrize("test", deepcopy(TESTS))
    def test_source(
        self,
        deploy_environment: DeployEnvironment,
        test: TypeDefTestDefinition,
        tmp_path: Path,
    ) -> None:
        """Test source."""
        assert (
            ModulePath(
                test["definition"],
                cache_dir=tmp_path,
                deploy_environment=deploy_environment,
            ).source
            == test["expected"]["source"]
        )

    @pytest.mark.parametrize("test", deepcopy(TESTS))
    def test_uri(
        self,
        deploy_environment: DeployEnvironment,
        test: TypeDefTestDefinition,
        tmp_path: Path,
    ) -> None:
        """Test uri."""
        assert (
            ModulePath(
                test["definition"],
                cache_dir=tmp_path,
                deploy_environment=deploy_environment,
            ).uri
            == test["expected"]["uri"]
        )

    def test_parse_obj_none(
        self, deploy_environment: DeployEnvironment, tmp_path: Path
    ) -> None:
        """Test parse_obj None."""
        obj = ModulePath.parse_obj(
            None, cache_dir=tmp_path, deploy_environment=deploy_environment
        )
        assert obj.definition == Path.cwd()
        assert obj.env == deploy_environment

    def test_parse_obj_path(
        self, deploy_environment: DeployEnvironment, tmp_path: Path
    ) -> None:
        """Test parse_obj Path."""
        obj = ModulePath.parse_obj(
            tmp_path, cache_dir=tmp_path, deploy_environment=deploy_environment
        )
        assert obj.definition == tmp_path
        assert obj.env == deploy_environment

    def test_parse_obj_runway_config(
        self, deploy_environment: DeployEnvironment, tmp_path: Path
    ) -> None:
        """Test parse_obj Runway config objects."""
        model = RunwayModuleDefinitionModel(path=tmp_path)
        obj0 = ModulePath.parse_obj(
            model, cache_dir=tmp_path, deploy_environment=deploy_environment
        )
        assert obj0.definition == model.path
        assert obj0.env == deploy_environment
        module = RunwayModuleDefinition(model)
        obj1 = ModulePath.parse_obj(
            module, cache_dir=tmp_path, deploy_environment=deploy_environment
        )
        assert obj1.definition == model.path
        assert obj1.env == deploy_environment

    def test_parse_obj_str(
        self, deploy_environment: DeployEnvironment, tmp_path: Path
    ) -> None:
        """Test parse_obj str."""
        obj = ModulePath.parse_obj(
            "./test", cache_dir=tmp_path, deploy_environment=deploy_environment
        )
        assert obj.definition == "./test"
        assert obj.env == deploy_environment

    def test_parse_obj_type_error(self, tmp_path: Path) -> None:
        """Test parse_obj TypeError."""
        with pytest.raises(TypeError):
            assert not ModulePath.parse_obj({}, cache_dir=tmp_path)  # type: ignore
