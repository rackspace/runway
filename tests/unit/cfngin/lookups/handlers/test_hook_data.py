"""Tests for runway.cfngin.lookups.handlers.hook_data."""
# pylint: disable=no-self-use
import pytest
from troposphere.awslambda import Code

from runway.cfngin.exceptions import FailedVariableLookup
from runway.variables import Variable


class TestHookDataLookup(object):
    """Tests for runway.cfngin.lookups.handlers.hook_data.HookDataLookup."""

    def test_handle(self, cfngin_context):
        """Test handle with simple usage."""
        cfngin_context.set_hook_data("fake_hook", {"nested": {"result": "good"}})
        var_top = Variable("test", "${hook_data fake_hook}", variable_type="cfngin")
        var_nested = Variable(
            "test", "${hook_data fake_hook.nested.result}", variable_type="cfngin"
        )
        var_top.resolve(cfngin_context)
        var_nested.resolve(cfngin_context)

        assert var_top.value == {"nested": {"result": "good"}}
        assert var_nested.value == "good"

    def test_default(self, cfngin_context):
        """Test handle with a default value."""
        cfngin_context.set_hook_data("fake_hook", {"nested": {"result": "good"}})
        var_top = Variable(
            "test", "${hook_data bad_hook::default=something}", variable_type="cfngin"
        )
        var_nested = Variable(
            "test",
            "${hook_data fake_hook.bad." "result::default=something,load=json,get=key}",
            variable_type="cfngin",
        )
        var_top.resolve(cfngin_context)
        var_nested.resolve(cfngin_context)

        assert var_top.value == "something"
        assert var_nested.value == "something"

    def test_not_found(self, cfngin_context):
        """Test value not found and no default."""
        variable = Variable(
            "test", "${hook_data fake_hook.bad.result}", variable_type="cfngin"
        )
        with pytest.raises(FailedVariableLookup) as err:
            variable.resolve(cfngin_context)

        assert "ValueError" in str(err.value)
        assert 'Could not find a value for "fake_hook.bad.result"' in str(err.value)

    def test_troposphere(self, cfngin_context):
        """Test with troposphere object like returned from lambda hook."""
        bucket = "test-bucket"
        s3_key = "lambda_functions/my_function"
        cfngin_context.set_hook_data(
            "lambda", {"my_function": Code(S3Bucket=bucket, S3Key=s3_key)}
        )
        var_bucket = Variable(
            "test",
            "${hook_data lambda.my_function::" "load=troposphere,get=S3Bucket}",
            variable_type="cfngin",
        )
        var_key = Variable(
            "test", "${hook_data lambda.my_function::get=S3Key}", variable_type="cfngin"
        )
        var_bucket.resolve(cfngin_context)
        var_key.resolve(cfngin_context)

        assert var_bucket.value == bucket
        assert var_key.value == s3_key

    def test_legacy_valid_hook_data(self, cfngin_context):
        """Test valid hook data."""
        cfngin_context.set_hook_data("fake_hook", {"result": "good"})
        variable = Variable(
            "test", "${hook_data fake_hook::result}", variable_type="cfngin"
        )
        with pytest.warns(DeprecationWarning):
            variable.resolve(cfngin_context)
        assert variable.value == "good"

    def test_legacy_invalid_hook_data(self, cfngin_context):
        """Test invalid hook data."""
        cfngin_context.set_hook_data("fake_hook", {"result": "good"})
        variable = Variable(
            "test", "${hook_data fake_hook::bad_key}", variable_type="cfngin"
        )
        with pytest.raises(FailedVariableLookup) as err, pytest.warns(
            DeprecationWarning
        ):
            variable.resolve(cfngin_context)

        assert "ValueError" in str(err.value)

    def test_legacy_bad_value_hook_data(self, cfngin_context):
        """Test bad value hook data."""
        variable = Variable(
            "test", "${hook_data fake_hook::bad_key}", variable_type="cfngin"
        )

        with pytest.raises(FailedVariableLookup) as err, pytest.warns(
            DeprecationWarning
        ):
            variable.resolve(cfngin_context)

        assert "ValueError" in str(err.value)
