"""Test runway.config.components.runway._deployment_dev."""

# pylint: disable=protected-access
# pyright: basic
from typing import Any, Dict, List

import pytest

from runway.config.components.runway import (
    RunwayDeploymentDefinition,
    RunwayModuleDefinition,
)
from runway.config.models.runway import (
    RunwayDeploymentDefinitionModel,
    RunwayModuleDefinitionModel,
)


class TestRunwayDeploymentDefinition:
    """Test runway.config.components.runway._deployment_dev.RunwayDeploymentDefinition."""

    @pytest.mark.parametrize(
        "data, expected",
        [
            (
                {"name": "test", "regions": ["us-east-1", "us-west-2"]},
                "test -  (us-east-1, us-west-2)",
            ),
            (
                {"name": "test", "modules": ["test-01.cfn"], "regions": ["us-east-1"]},
                "test - test-01.cfn (us-east-1)",
            ),
            (
                {
                    "name": "test",
                    "modules": ["test-01.cfn", "test-02.cfn"],
                    "regions": ["us-east-1"],
                },
                "test - test-01.cfn, test-02.cfn (us-east-1)",
            ),
            (
                {"name": "test", "parallel_regions": ["us-east-1", "us-west-2"]},
                "test -  (us-east-1, us-west-2)",
            ),
            (
                {
                    "name": "test",
                    "modules": ["test-01.cfn"],
                    "parallel_regions": ["us-east-1"],
                },
                "test - test-01.cfn (us-east-1)",
            ),
            (
                {
                    "name": "test",
                    "modules": ["test-01.cfn", "test-02.cfn"],
                    "parallel_regions": ["us-east-1"],
                },
                "test - test-01.cfn, test-02.cfn (us-east-1)",
            ),
            (
                {"name": "test", "modules": ["test-01.cfn"], "regions": "${var test}"},
                "test - test-01.cfn (${var test})",
            ),
            (
                {
                    "name": "test",
                    "modules": ["test-01.cfn"],
                    "parallel_regions": "${var test}",
                },
                "test - test-01.cfn (${var test})",
            ),
        ],
    )
    def test_menu_entry(self, data: Dict[str, Any], expected: str) -> None:
        """Test menu_entry."""
        assert RunwayDeploymentDefinition.parse_obj(data).menu_entry == expected

    def test_modules(self) -> None:
        """Test modules."""
        result = RunwayDeploymentDefinition.parse_obj(
            {"modules": ["test.cfn"], "regions": ["us-east-1"]}
        ).modules
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], RunwayModuleDefinition)
        assert result[0].name == "test.cfn"

    def test_modules_setter(self) -> None:
        """Test modules.setter."""
        obj = RunwayDeploymentDefinition.parse_obj({"regions": ["us-east-1"]})
        new_modules = [
            RunwayModuleDefinition.parse_obj({"path": "./", "name": "test-01"}),
            RunwayModuleDefinition.parse_obj({"name": "test-02", "path": "./"}),
        ]
        obj.modules = new_modules
        assert obj._data.modules[0] == new_modules[0].data
        assert obj._data.modules[1] == new_modules[1].data

    def test_modules_setter_not_list(self) -> None:
        """Test modules.setter not a list."""
        obj = RunwayDeploymentDefinition.parse_obj({"regions": ["us-east-1"]})
        with pytest.raises(TypeError):
            obj.modules = "invalid"  # type: ignore
        with pytest.raises(TypeError):
            obj.modules = {"key": "val"}  # type: ignore
        with pytest.raises(TypeError):
            obj.modules = None  # type: ignore
        with pytest.raises(TypeError):
            obj.modules = [  # type: ignore
                RunwayDeploymentDefinitionModel(
                    modules=[], name="test-01", regions=["us-east-1"]
                )
            ]

    def test_models_setter_invalid_list_item(self) -> None:
        """Test modules.setter when list item is now supported."""
        with pytest.raises(TypeError):
            obj = RunwayDeploymentDefinition.parse_obj({"regions": ["us-east-1"]})
            obj.modules = [RunwayModuleDefinitionModel(path="./"), "invalid"]  # type: ignore

    def test_parse_obj(self) -> None:
        """Test parse_obj."""
        data: Dict[str, Any] = {"name": "test", "modules": [], "regions": ["us-east-1"]}
        obj = RunwayDeploymentDefinition.parse_obj(data)
        assert obj._data.dict(exclude_unset=True) == data

    def test_parse_obj_list(self) -> None:
        """Test parse_obj list."""
        data: List[Dict[str, Any]] = [
            {"name": "test", "modules": [], "regions": ["us-east-1"]}
        ]
        result = RunwayDeploymentDefinition.parse_obj(data)

        assert isinstance(result, list)
        assert len(result) == 1
        # for some reason, the current version of pylint does not see this as list
        # pylint: disable=unsubscriptable-object
        assert result[0]._data.dict(exclude_unset=True) == data[0]

    def test_register_variable(self) -> None:
        """Test _register_variable."""
        obj = RunwayDeploymentDefinition.parse_obj(
            {"name": "test", "regions": ["us-east-1"]}
        )
        assert obj._vars["regions"].name == "test.regions"

    def test_reverse(self) -> None:
        """Test reverse."""
        data: RunwayDeploymentDefinitionModel = (
            RunwayDeploymentDefinitionModel.parse_obj(
                {
                    "name": "test",
                    "modules": [
                        {"name": "test-01", "path": "./"},
                        {"name": "test-02", "path": "./"},
                    ],
                    "regions": ["us-east-1", "us-west-2"],
                }
            )
        )
        obj = RunwayDeploymentDefinition(data)
        assert not obj.reverse()
        assert obj._data.modules != data.modules
        assert obj._data.regions != data.regions
        assert obj.regions == ["us-west-2", "us-east-1"]
        assert obj._data.modules == [data.modules[1], data.modules[0]]

    def test_reverse_parallel_modules(self) -> None:
        """Test reverse parallel modules."""
        data: RunwayDeploymentDefinitionModel = (
            RunwayDeploymentDefinitionModel.parse_obj(
                {
                    "name": "test",
                    "modules": [
                        {
                            "parallel": [
                                {"name": "test-01", "path": "./"},
                                {"name": "test-02", "path": "./"},
                            ]
                        },
                    ],
                    "regions": ["us-east-1", "us-west-2"],
                }
            )
        )
        obj = RunwayDeploymentDefinition(data)
        assert not obj.reverse()
        assert obj._data.modules != data.modules
        invert_data: RunwayDeploymentDefinitionModel = data.copy(deep=True)
        for mod in invert_data.modules:
            mod.parallel.reverse()
        assert obj._data.modules == invert_data.modules

    def test_reverse_parallel_regions(self) -> None:
        """Test reverse parallel regions."""
        data: RunwayDeploymentDefinitionModel = (
            RunwayDeploymentDefinitionModel.parse_obj(
                {
                    "name": "test",
                    "modules": [{"name": "test-01", "path": "./"}],
                    "parallel_regions": ["us-east-1", "us-west-2"],
                }
            )
        )
        obj = RunwayDeploymentDefinition(data)
        assert not obj.reverse()
        assert obj._data.parallel_regions != data.parallel_regions
        assert obj.parallel_regions == ["us-west-2", "us-east-1"]
