"""Test runway.module.__init__."""
# pylint: disable=no-self-use,unused-argument
import logging
import sys
from contextlib import contextmanager

import pytest
from mock import MagicMock, call, patch

from runway.module import NPM_BIN, ModuleOptions, RunwayModuleNpm

if sys.version_info[0] > 2:  # TODO remove after droping python 2
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E


@contextmanager
def does_not_raise():
    """Use for conditional pytest.raises when using parametrize."""
    yield


class TestRunwayModuleNpm(object):
    """Test runway.module.RunwayModuleNpm."""

    @patch("runway.module.which")
    @patch("runway.module.warn_on_boto_env_vars", MagicMock(return_value=None))
    def test_check_for_npm(self, mock_which, caplog, runway_context):
        """Test check_for_npm."""
        mock_which.side_effect = [
            "something",  # first call during init
            None,
        ]  # explicit call
        obj = RunwayModuleNpm(context=runway_context, path="./tests", options={})
        caplog.set_level(logging.WARNING, logger="runway")

        with pytest.raises(SystemExit):
            assert not obj.check_for_npm()

        assert [
            '"npm" not found in path or is not executable; '
            "please ensure it is installed correctly"
        ] == caplog.messages

    @patch("runway.module.which")
    @patch("runway.module.warn_on_boto_env_vars")
    def test_init(self, mock_warn, mock_which, caplog, runway_context, tmp_path):
        """Test init and the attributes set in init."""
        # pylint: disable=no-member
        caplog.set_level(logging.ERROR, logger="runway")
        mock_which.side_effect = [True, True, False]
        options = {
            "environments": True,  # can only be True of a falsy value (but not dict)
            "options": {"test_option": "option_value"},
            "parameters": {"test_parameter": "parameter_value"},
            "extra": "something",
        }
        obj = RunwayModuleNpm(
            context=runway_context,  # side_effect[0]
            path=str(tmp_path),
            options=options.copy(),
        )

        mock_which.assert_called_once()
        assert obj.context == runway_context
        assert obj.environments == options["environments"]
        assert obj.extra == options["extra"]
        assert obj.options == options["options"]
        assert obj.parameters == options["parameters"]
        assert isinstance(obj.path, Path)
        assert str(obj.path) == str(tmp_path)
        mock_warn.assert_called_once_with(runway_context.env_vars)

        obj = RunwayModuleNpm(context=runway_context, path=tmp_path)  # side_effect[1]
        assert not obj.environments
        assert not obj.options
        assert not obj.parameters
        assert obj.path == tmp_path

        caplog.clear()
        with pytest.raises(SystemExit) as excinfo:
            obj = RunwayModuleNpm(
                context=runway_context, path=tmp_path  # side_effect[2]
            )
        assert excinfo.value.code > 0  # non-zero exit code
        assert caplog.messages == [
            '"npm" not found in path or is not executable; '
            "please ensure it is installed correctly"
        ]

    @patch("runway.module.format_npm_command_for_logging")
    def test_log_npm_command(self, mock_log, caplog, patch_module_npm, runway_context):
        """Test log_npm_command."""
        mock_log.return_value = "success"
        obj = RunwayModuleNpm(context=runway_context, path="./tests", options={})
        caplog.set_level(logging.DEBUG, logger="runway")
        assert not obj.log_npm_command(["npm", "test"])
        mock_log.assert_called_once_with(["npm", "test"])
        assert ["node command: success"] == caplog.messages

    @patch("runway.module.use_npm_ci")
    @patch("runway.module.subprocess")
    def test_npm_install(
        self, moc_proc, mock_ci, caplog, monkeypatch, patch_module_npm, runway_context
    ):
        """Test npm_install."""
        monkeypatch.setattr(runway_context, "no_color", False)
        caplog.set_level(logging.INFO, logger="runway")
        obj = RunwayModuleNpm(context=runway_context, path="./tests", options={})
        expected_logs = []
        expected_calls = []

        obj.options["skip_npm_ci"] = True
        assert not obj.npm_install()
        expected_logs.append("skipped npm ci/npm install")

        obj.options["skip_npm_ci"] = False
        obj.context.env.ci = True
        mock_ci.return_value = True
        assert not obj.npm_install()
        expected_logs.append("running npm ci...")
        expected_calls.append(call([NPM_BIN, "ci"]))

        obj.context.env.ci = False
        assert not obj.npm_install()
        expected_logs.append("running npm install...")
        expected_calls.append(call([NPM_BIN, "install"]))

        obj.context.env.ci = True
        mock_ci.return_value = False
        assert not obj.npm_install()
        expected_logs.append("running npm install...")
        expected_calls.append(call([NPM_BIN, "install"]))

        monkeypatch.setattr(runway_context, "no_color", True)
        assert not obj.npm_install()
        expected_logs.append("running npm install...")
        expected_calls.append(call([NPM_BIN, "install", "--no-color"]))

        obj.options["skip_npm_ci"] = False
        obj.context.env.ci = True
        mock_ci.return_value = True
        assert not obj.npm_install()
        expected_logs.append("running npm ci...")
        expected_calls.append(call([NPM_BIN, "ci", "--no-color"]))

        assert expected_logs == caplog.messages
        moc_proc.check_call.assert_has_calls(expected_calls)

    def test_package_json_missing(
        self, caplog, patch_module_npm, runway_context, tmp_path
    ):
        """Test package_json_missing."""
        caplog.set_level(logging.DEBUG, logger="runway")
        obj = RunwayModuleNpm(context=runway_context, path=str(tmp_path), options={})

        assert obj.package_json_missing()
        assert ["module is missing package.json"] == caplog.messages

        (tmp_path / "package.json").touch()
        assert not obj.package_json_missing()


class TestModuleOptions(object):
    """Test runway.module.ModuleOptions."""

    @pytest.mark.parametrize(
        "data, env, expected, exception",
        [
            ("test", None, "test", does_not_raise()),
            ("test", "env", "test", does_not_raise()),
            ({"key": "value"}, "test", {"key": "called"}, does_not_raise()),
            ({"key": "value"}, None, {"key": "called"}, does_not_raise()),
            (["test"], None, ["test"], does_not_raise()),
            (["test"], "env", ["test"], does_not_raise()),
            (None, None, None, does_not_raise()),
            (None, "env", None, does_not_raise()),
            (100, None, None, pytest.raises(TypeError)),
            (100, "env", None, pytest.raises(TypeError)),
        ],
    )
    @pytest.mark.skipif(
        sys.version_info.major < 3,
        reason="python 2 does not handle unbound functions " "being patched in",
    )
    def test_merge_nested_env_dicts(self, monkeypatch, data, env, expected, exception):
        """Test merge_nested_env_dicts."""

        def merge_nested_environment_dicts(value, env_name):
            """Assert args passed to the method during parse."""
            assert value == list(data.values())[0]  # only pass data dict of 1 item
            assert env_name == env
            return "called"

        monkeypatch.setattr(
            "runway.module.merge_nested_environment_dicts",
            merge_nested_environment_dicts,
        )

        with exception:
            assert ModuleOptions.merge_nested_env_dicts(data, env) == expected

    def test_parse(self, runway_context):
        """Test parse."""
        with pytest.raises(NotImplementedError):
            assert ModuleOptions.parse(runway_context)

    @pytest.mark.parametrize("value", ["test", None, 123, {"key": "val"}])
    def test_mutablemapping_abstractmethods(self, value):
        """Test the abstractmethods of MutableMapping."""
        obj = ModuleOptions()
        obj["key"] = value  # __setitem__
        assert obj["key"] == value, "test __setitem__ and __getitem__"
        assert isinstance(obj["key"], type(value)), "test type retention"
        assert obj.get("key") == value, "ensure .get() is working"
        assert len(obj) == 1, "test __len__"

        counter = 0
        for _ in obj:
            counter += 1
        assert counter == 1, "test __iter__"

        del obj["key"]
        assert "key" not in obj, "test __delitem__ with __contains__"
        with pytest.raises(KeyError):
            assert obj["key"], "test __delitem__ with __getitem__"
