"""Test runway.module.staticsite.options.components."""

# pyright: basic
from __future__ import annotations

from runway.module.staticsite.options.components import StaticSiteOptions
from runway.module.staticsite.options.models import (
    RunwayStaticSiteModuleOptionsDataModel,
    RunwayStaticSitePreBuildStepDataModel,
)

MODULE = "runway.module.staticsite.options.components"


class TestStaticSiteOptions:
    """Test StaticSiteOptions."""

    def test_init(self) -> None:
        """Test __init__."""
        data = RunwayStaticSiteModuleOptionsDataModel(
            build_output="./dist",
            build_steps=["runway --help"],
            pre_build_steps=[
                RunwayStaticSitePreBuildStepDataModel(command="runway --help")
            ],
        )
        obj = StaticSiteOptions(data=data)
        assert obj.build_output == data.build_output
        assert obj.build_steps == data.build_steps
        assert obj.data == data
        assert obj.extra_files == data.extra_files
        assert obj.pre_build_steps == data.pre_build_steps
        assert obj.source_hashing == data.source_hashing

    def test_parse_obj(self) -> None:
        """Test parse_obj."""
        obj = StaticSiteOptions.parse_obj({})
        assert isinstance(obj.data, RunwayStaticSiteModuleOptionsDataModel)
        assert (
            obj.data.dict(exclude_defaults=True, exclude_none=True, exclude_unset=True)
            == {}
        )
