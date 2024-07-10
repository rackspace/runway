"""Test runway.config.components.runway._module_def."""

# pyright: basic
from pathlib import Path
from typing import Any, Dict

import pytest

from runway.config.components.runway import RunwayModuleDefinition
from runway.config.models.runway import RunwayModuleDefinitionModel


class TestRunwayModuleDefinition:
    """Test runway.config.components.runway._module_def.RunwayModuleDefinition."""

    def test_child_modules(self) -> None:
        """Test child_modules."""
        data = {"parallel": [{"name": "test", "path": "./"}]}
        result = RunwayModuleDefinition.parse_obj(data).child_modules
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], RunwayModuleDefinition)
        assert result[0].name == data["parallel"][0]["name"]
        assert RunwayModuleDefinition.parse_obj({"path": "./"}).child_modules == []

    def test_child_modules_setter(self) -> None:
        """Test child_modules.setter."""
        obj = RunwayModuleDefinition.parse_obj({"parallel": [{"path": "./"}]})
        new_modules = [
            RunwayModuleDefinitionModel(path="./", name="test-01"),
            RunwayModuleDefinition.parse_obj({"name": "test-02", "path": "./"}),
        ]
        obj.child_modules = new_modules
        assert obj._data.parallel[0] == new_modules[0]
        assert obj._data.parallel[1] == new_modules[1].data  # type: ignore

    def test_child_modules_setter_not_list(self) -> None:
        """Test child_modules.setter not a list."""
        obj = RunwayModuleDefinition.parse_obj({"path": "./"})
        with pytest.raises(TypeError):
            obj.child_modules = "invalid"  # type: ignore
        with pytest.raises(TypeError):
            obj.child_modules = {"key": "val"}  # type: ignore
        with pytest.raises(TypeError):
            obj.child_modules = None  # type: ignore

    def test_child_modules_setter_invalid_list_item(self) -> None:
        """Test child_modules.setter when list item is now supported."""
        with pytest.raises(TypeError):
            obj = RunwayModuleDefinition.parse_obj({"path": "./"})
            obj.child_modules = [  # type: ignore
                RunwayModuleDefinitionModel(path="./"),
                "invalid",
            ]

    @pytest.mark.parametrize(
        "data, expected",
        [
            ({"name": "parallel_parent", "path": "./"}, False),
            ({"path": "./"}, False),
            (
                {
                    "parallel": [
                        {"name": "test-01", "path": "./"},
                        {"name": "test-02", "path": "./"},
                    ],
                },
                True,
            ),
            ({"name": "test", "parallel": [{"name": "test-01", "path": "./"}]}, True),
            (
                {
                    "name": "test",
                    "parallel": [
                        {"name": "test-01", "path": "./"},
                        {"name": "test-02", "path": "./"},
                    ],
                },
                True,
            ),
        ],
    )
    def test_is_parent(self, data: Dict[str, Any], expected: bool) -> None:
        """Test is_parent."""
        assert RunwayModuleDefinition.parse_obj(data).is_parent is expected

    @pytest.mark.parametrize(
        "data, expected",
        [
            ({"path": "./"}, Path.cwd().name),
            ({"name": "test", "path": "./"}, "test"),
            (
                {
                    "name": "test",
                    "parallel": [
                        {"name": "test-01", "path": "./"},
                        {"name": "test-02", "path": "./"},
                    ],
                },
                "test [test-01, test-02]",
            ),
            (
                {
                    "parallel": [
                        {"name": "test-01", "path": "./"},
                        {"name": "test-02", "path": "./"},
                    ],
                },
                "parallel_parent [test-01, test-02]",
            ),
            (
                {"name": "test", "parallel": [{"name": "test-01", "path": "./"}]},
                "test [test-01]",
            ),
        ],
    )
    def test_menu_entry(self, data: Dict[str, Any], expected: str) -> None:
        """Test menu entry."""
        assert RunwayModuleDefinition.parse_obj(data).menu_entry == expected

    def test_parse_obj(self) -> None:
        """Test parse_obj."""
        data = {"name": Path.cwd().name, "path": "./"}
        obj = RunwayModuleDefinition.parse_obj(data)
        assert obj._data.dict(exclude_unset=True) == data

    def test_register_variable(self) -> None:
        """Test _register_variable."""
        obj = RunwayModuleDefinition.parse_obj({"name": "test", "path": "./"})
        assert obj._vars["path"].name == "test.path"

    def test_reverse(self) -> None:
        """Test reverse."""
        data: RunwayModuleDefinitionModel = RunwayModuleDefinitionModel.parse_obj(
            {
                "name": "parallel_parent",
                "parallel": [
                    {"name": "test-01", "path": "./"},
                    {"name": "test-02", "path": "./"},
                ],
            }
        )
        obj = RunwayModuleDefinition(data)
        assert not obj.reverse()
        assert obj._data.parallel != data.parallel
        assert obj._data.parallel == [data.parallel[1], data.parallel[0]]
