"""Test runway.exceptions."""

from __future__ import annotations

import pickle
from typing import TYPE_CHECKING, Any

import pytest

from runway.cfngin.exceptions import (
    CfnginBucketAccessDenied,
    CfnginBucketNotFound,
    CfnginBucketRequired,
    CfnginOnlyLookupError,
    ChangesetDidNotStabilize,
    GraphError,
    ImproperlyConfigured,
    InvalidConfig,
    InvalidDockerizePipConfiguration,
    InvalidUserdataPlaceholder,
    MissingEnvironment,
    MissingParameterException,
    MissingVariable,
    PersistentGraphCannotLock,
    PersistentGraphCannotUnlock,
    PersistentGraphLockCodeMismatch,
    PersistentGraphLocked,
    PersistentGraphUnlocked,
    PlanFailed,
    StackDoesNotExist,
    StackFailed,
    StackUpdateBadStatus,
    UnableToExecuteChangeSet,
    UnhandledChangeSetStatus,
    UnresolvedBlueprintVariable,
    UnresolvedBlueprintVariables,
    ValidatorError,
    VariableTypeRequired,
)
from runway.cfngin.plan import Step
from runway.cfngin.stack import Stack
from runway.config import CfnginStackDefinitionModel
from runway.core.components import DeployEnvironment
from runway.exceptions import (
    ConfigNotFound,
    DockerExecFailedError,
    FailedLookup,
    FailedVariableLookup,
    InvalidLookupConcatenation,
    OutputDoesNotExist,
    RequiredTagNotFoundError,
)
from runway.variables import (
    Variable,
    VariableValue,
    VariableValueConcatenation,
    VariableValueLiteral,
    VariableValueLookup,
)

from .factories import MockCfnginContext

if TYPE_CHECKING:
    from pathlib import Path


def generate_stack_definition(
    base_name: str, stack_id: Any = None, **overrides: Any
) -> CfnginStackDefinitionModel:
    """Generate stack definition."""
    definition: dict[str, Any] = {
        "name": f"{base_name}-{stack_id}" if stack_id else base_name,
        "class_path": f"tests.unit.cfngin.fixtures.mock_blueprints.{base_name.upper()}",
        "requires": [],
    }
    definition.update(overrides)
    return CfnginStackDefinitionModel(**definition)


@pytest.fixture
def variable() -> Variable:
    """Return a Variable instance."""
    return Variable(name="test", value="test")


@pytest.fixture
def step() -> Step:
    """Return a Step instance."""
    stack = Stack(
        definition=generate_stack_definition(
            base_name="vpc",
            required_by=["fakeStack0"],
            variables={"Param1": "${output fakeStack.FakeOutput}"},
        ),
        context=MockCfnginContext(deploy_environment=DeployEnvironment()),
    )
    stack.name = "stack"
    stack.fqn = "namespace-stack"
    return Step(stack=stack, fn=None)


class TestConfigNotFound:
    """Test "ConfigNotFound."""

    def test_pickle(self, tmp_path: Path) -> None:
        """Test pickling."""
        exc = ConfigNotFound(["foo"], tmp_path)
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestDockerExecFailedError:
    """Test "DockerExecFailedError."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = DockerExecFailedError({"StatusCode": 1})
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestFailedLookup:
    """Test "FailedLookup."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = FailedLookup("foo", "bar")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestFailedVariableLookup:
    """Test "FailedVariableLookup."""

    def test_pickle(self, variable: Variable) -> None:
        """Test pickling."""
        exc = FailedVariableLookup(
            variable,
            FailedLookup(
                VariableValueLookup(VariableValueLiteral("env"), "foo"), Exception("error")
            ),
        )
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestInvalidLookupConcatenation:
    """Test "InvalidLookupConcatenation."""

    def test_pickle(self) -> None:
        """Test pickling."""
        data = [VariableValueLiteral("test")]
        exc = InvalidLookupConcatenation(
            VariableValue.parse_obj("test"), VariableValueConcatenation(data)
        )
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestOutputDoesNotExist:
    """Test "OutputDoesNotExist."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = OutputDoesNotExist("foo", "bar")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestRequiredTagNotFoundError:
    """Test "RequiredTagNotFoundError."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = RequiredTagNotFoundError("foo", "bar")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestVariableTypeRequired:
    """Test "VariableTypeRequired."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = VariableTypeRequired("blueprint_name", "variable_name")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestCfnginBucketAccessDenied:
    """Test "CfnginBucketAccessDenied."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = CfnginBucketAccessDenied("foo")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestCfnginBucketNotFound:
    """Test "CfnginBucketNotFound."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = CfnginBucketNotFound("foo")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestCfnginBucketRequired:
    """Test "CfnginBucketRequired."""

    def test_pickle(self, tmp_path: Path) -> None:
        """Test pickling."""
        exc = CfnginBucketRequired(config_path=tmp_path, reason="reason")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestCfnginOnlyLookupError:
    """Test "CfnginOnlyLookupError."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = CfnginOnlyLookupError("lookup_name")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestChangesetDidNotStabilize:
    """Test "ChangesetDidNotStabilize."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = ChangesetDidNotStabilize("change_set_id")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestGraphError:
    """Test "GraphError."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = GraphError(exception=Exception("error"), stack="stack", dependency="dependency")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestImproperlyConfigured:
    """Test "ImproperlyConfigured."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = ImproperlyConfigured(kls="Class", error=Exception("error"))
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestInvalidConfig:
    """Test "InvalidConfig."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = InvalidConfig(Exception("error"))
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestInvalidDockerizePipConfiguration:
    """Test "InvalidDockerizePipConfiguration."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = InvalidDockerizePipConfiguration("Invalid configuration")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestInvalidUserdataPlaceholder:
    """Test "InvalidUserdataPlaceholder."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = InvalidUserdataPlaceholder("blueprint_name", "exception_message")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestMissingEnvironment:
    """Test "MissingEnvironment."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = MissingEnvironment("key")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestMissingParameterException:
    """Test "MissingParameterException."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = MissingParameterException(["param1", "param2"])
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestMissingVariable:
    """Test "MissingVariable."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = MissingVariable("blueprint_name", "variable_name")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestPersistentGraphCannotLock:
    """Test "PersistentGraphCannotLock."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = PersistentGraphCannotLock("reason")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestPersistentGraphCannotUnlock:
    """Test "PersistentGraphCannotUnlock."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = PersistentGraphCannotUnlock("reason")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestPersistentGraphLocked:
    """Test "PersistentGraphLocked."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = PersistentGraphLocked("foo", "bar")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestPersistentGraphLockCodeMismatch:
    """Test "PersistentGraphLockCodeMismatch."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = PersistentGraphLockCodeMismatch("provided_code", "s3_code")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestPersistentGraphUnlocked:
    """Test "PersistentGraphUnlocked."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = PersistentGraphUnlocked("message", "reason")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestPlanFailed:
    """Test "PlanFailed."""

    def test_pickle(self, step: Step) -> None:
        """Test pickling."""
        exc = PlanFailed([step])
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestStackDoesNotExist:
    """Test "StackDoesNotExist."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = StackDoesNotExist("stack_name")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestStackUpdateBadStatus:
    """Test "StackUpdateBadStatus."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = StackUpdateBadStatus("stack_name", "stack_status", "reason")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestStackFailed:
    """Test "StackFailed."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = StackFailed("stack_name", "status_reason")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestUnableToExecuteChangeSet:
    """Test "UnableToExecuteChangeSet."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = UnableToExecuteChangeSet("stack_name", "change_set_id", "execution_status")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestUnhandledChangeSetStatus:
    """Test "UnhandledChangeSetStatus."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = UnhandledChangeSetStatus("stack_name", "change_set_id", "status", "status_reason")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestUnresolvedBlueprintVariable:
    """Test "UnresolvedBlueprintVariable."""

    def test_pickle(self, variable: Variable) -> None:
        """Test pickling."""
        exc = UnresolvedBlueprintVariable("blueprint_name", variable)
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestUnresolvedBlueprintVariables:
    """Test "UnresolvedBlueprintVariables."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = UnresolvedBlueprintVariables("blueprint_name")
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)


class TestValidatorError:
    """Test "ValidatorError."""

    def test_pickle(self) -> None:
        """Test pickling."""
        exc = ValidatorError("variable", "validator", "value", Exception("error"))
        assert str(pickle.loads(pickle.dumps(exc))) == str(exc)
