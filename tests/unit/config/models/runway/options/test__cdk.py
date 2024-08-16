"""Test runway.config.models.runway.options.cdk."""

from runway.config.models.runway.options.cdk import RunwayCdkModuleOptionsDataModel


class TestRunwayCdkModuleOptionsDataModel:
    """Test RunwayCdkModuleOptionsDataModel."""

    def test_init_default(self) -> None:
        """Test init default."""
        obj = RunwayCdkModuleOptionsDataModel()
        assert not obj.build_steps
        assert isinstance(obj.build_steps, list)
        assert not obj.skip_npm_ci

    def test_init_extra(self) -> None:
        """Test init extra."""
        obj = RunwayCdkModuleOptionsDataModel.model_validate({"invalid": "val"})
        assert "invalid" not in obj.model_dump()

    def test_init(self) -> None:
        """Test init."""
        obj = RunwayCdkModuleOptionsDataModel(build_steps=["test0", "test1"], skip_npm_ci=True)
        assert obj.build_steps == ["test0", "test1"]
        assert obj.skip_npm_ci
