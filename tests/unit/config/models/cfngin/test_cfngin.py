"""Test runway.config.models.cfngin.__init__."""
# pylint: disable=no-self-use
import pytest
from pydantic import ValidationError

from runway.config.models.cfngin import Hook, Stack, Target


class TestHook:
    """Test runway.config.models.cfngin.Hook."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            Hook(invalid="something", path="something")
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = Hook(path="something")
        assert obj.args == {}
        assert not obj.data_key
        assert obj.enabled
        assert obj.path == "something"
        assert obj.required

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            Hook()
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("path",)
        assert errors[0]["msg"] == "field required"


class TestStack:
    """Test runway.config.models.cfngin.Stack."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            Stack(class_path="something", invalid="something", name="stack-name")
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = Stack(class_path="something", name="stack-name")
        assert obj.class_path == "something"
        assert not obj.description
        assert obj.enabled
        assert not obj.in_progress_behavior
        assert not obj.locked
        assert obj.name == "stack-name"
        assert not obj.profile
        assert not obj.protected
        assert not obj.region
        assert obj.required_by == []
        assert obj.requires == []
        assert not obj.stack_name
        assert not obj.stack_policy_path
        assert obj.tags == {}
        assert not obj.template_path
        assert not obj.termination_protection
        assert obj.variables == {}

    def test_required_fields(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            Stack()
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("__root__",)
        assert errors[0]["msg"] == "either class_path or template_path must be defined"

    def test_resolve_path_fields(self) -> None:
        """Test _resolve_path_fields."""
        obj = Stack(
            name="test-stack",
            stack_policy_path="./policy.json",
            template_path="./template.yml",
        )
        assert obj.stack_policy_path.is_absolute()
        assert obj.template_path.is_absolute()

    def test_required_fields_w_class_path(self) -> None:
        """Test required fields."""
        with pytest.raises(ValidationError) as excinfo:
            Stack(class_path="something")
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert errors[0]["msg"] == "field required"

    def test_validate_class_and_template(self) -> None:
        """Test _validate_class_and_template."""
        with pytest.raises(ValidationError) as excinfo:
            Stack(
                class_path="something",
                name="stack-name",
                template_path="./something.yml",
            )
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("__root__",)
        assert (
            errors[0]["msg"] == "only one of class_path or template_path can be defined"
        )

    @pytest.mark.parametrize(
        "enabled, locked", [(True, True), (False, True), (False, False)]
    )
    def test_validate_class_or_template(self, enabled: bool, locked: bool) -> None:
        """Test _validate_class_or_template."""
        assert Stack(
            class_path="something", enabled=enabled, locked=locked, name="test-stack"
        )
        assert Stack(
            enabled=enabled,
            locked=locked,
            name="test-stack",
            template_path="./something.yml",
        )

    def test_validate_class_or_template_invalid(self) -> None:
        """Test _validate_class_or_template invalid."""
        with pytest.raises(ValidationError) as excinfo:
            Stack(
                enabled=True, locked=False, name="stack-name",
            )
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("__root__",)
        assert errors[0]["msg"] == "either class_path or template_path must be defined"


class TestTarget:
    """Test runway.config.models.cfngin.Target."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            Target(invalid="something", name="something")
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = Target(name="something")
        assert obj.name == "something"
        assert obj.required_by == []
        assert obj.requires == []
