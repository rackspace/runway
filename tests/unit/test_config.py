"""Test Runway config classes."""
# pylint: disable=no-self-use,redefined-outer-name
import logging
import os
from copy import deepcopy
from tempfile import NamedTemporaryFile

import pytest
import yaml
from mock import MagicMock, call, patch
from packaging.specifiers import InvalidSpecifier

from runway.cfngin.exceptions import UnresolvedVariable
from runway.config import (  # tries to test the imported class unless using "as"
    Config,
    DeploymentDefinition,
    FutureDefinition,
    ModuleDefinition,
)
from runway.config import TestDefinition as ConfigTestDefinition
from runway.config import VariablesDefinition
from runway.util import MutableMap

MODULE = "runway.config"
YAML_FIXTURES = ["config.runway.yml", "config.runway.variables.yml"]
ENV_VARS = {"AWS_REGION": "us-east-1", "DEPLOY_ENVIRONMENT": "test", "USER": "test"}


@pytest.fixture
def patch_config_subcomponents(monkeypatch):
    """Patch subcomponents with Mock objects to test Config base class."""
    mocks = {
        "deployment": MagicMock(spec=DeploymentDefinition),
        "future": MagicMock(spec=FutureDefinition),
        "test": MagicMock(spec=ConfigTestDefinition),
        "variables": MagicMock(spec=VariablesDefinition),
    }
    monkeypatch.setattr(MODULE + ".DeploymentDefinition", mocks["deployment"])
    monkeypatch.setattr(MODULE + ".FutureDefinition", mocks["future"])
    monkeypatch.setattr(MODULE + ".TestDefinition", mocks["test"])
    monkeypatch.setattr(MODULE + ".VariablesDefinition", mocks["variables"])
    return mocks


class TestConfig(object):
    """Test runway.config.Config."""

    @patch(MODULE + ".SpecifierSet")
    def test_init(self, mock_specifier, patch_config_subcomponents):
        """Test init."""
        mocks = patch_config_subcomponents
        raw_config = {
            "deployments": [{"modules": "val"}],
            "future": {"some_future": True},
            "ignore_git_branch": True,
            "runway_version": "<2.0",
            "tests": [{"name": "test"}],
            "variables": {"some_var": "val"},
        }
        config = Config(**raw_config)

        mocks["deployment"].from_list.assert_called_once_with(raw_config["deployments"])
        mocks["future"].assert_called_once_with(**raw_config["future"])
        mocks["test"].from_list.assert_called_once_with(raw_config["tests"])
        mocks["variables"].load.assert_called_once_with(**raw_config["variables"])
        mock_specifier.assert_called_once_with(
            raw_config["runway_version"], prereleases=True
        )
        assert config.deployments == mocks["deployment"].from_list.return_value
        assert config.future == mocks["future"].return_value
        assert config.ignore_git_branch
        assert config.runway_version == mock_specifier.return_value
        assert config.tests == mocks["test"].from_list.return_value
        assert config.variables == mocks["variables"].load.return_value

    @patch(MODULE + ".SpecifierSet")
    def test_init_default(self, mock_specifier, patch_config_subcomponents):
        """Test init using default values."""
        mocks = patch_config_subcomponents
        deployments = [{"key": "val"}]
        config = Config(deployments)

        mocks["deployment"].from_list.assert_called_once_with([{"key": "val"}])
        mocks["future"].assert_called_once_with()
        mocks["test"].from_list.assert_called_once_with(None)
        mocks["variables"].load.assert_called_once_with()
        mock_specifier.assert_called_once_with(">1.10", prereleases=True)
        assert not config.ignore_git_branch

    @patch(MODULE + ".SpecifierSet")
    def test_init_invalidspecifier(self, mock_specifier, patch_config_subcomponents):
        """Test init with InvalidSpecifier."""
        mock_specifier.side_effect = InvalidSpecifier

        # no retry
        with pytest.raises(InvalidSpecifier):
            assert Config([])
        mock_specifier.assert_called_once_with(">1.10", prereleases=True)

        # retry with exact version
        mock_specifier.side_effect = [InvalidSpecifier, "success"]
        config = Config([], runway_version=1.11)
        mock_specifier.assert_has_calls(
            [call("1.11", prereleases=True), call("==1.11", prereleases=True)]
        )
        assert config.runway_version == "success"


class TestDeploymentDefinition(object):
    """Test DeploymentDefinition."""

    ATTRS = [
        "_account_alias",
        "_account_id",
        "_assume_role",
        "_env_vars",
        "_environments",
        "_module_options",
        "modules",
        "name",
        "_regions",
        "_parallel_regions",
    ]

    def test_from_list(self, yaml_fixtures):
        """Test init of a deployment from a list."""
        raw_config = deepcopy(yaml_fixtures["config.runway.yml"]["deployments"])
        deployment = DeploymentDefinition.from_list(raw_config)[0]
        deployment_attrs = deployment.__dict__.keys()

        assert deployment.name == "deployment_1"

        for attr in self.ATTRS:  # provides a better error than using all()
            assert attr in deployment_attrs

    def test_pre_process_resolve(self, yaml_fixtures):
        """Test that pre-process resolution only resolves specific vars."""
        raw_config = deepcopy(yaml_fixtures["config.runway.yml"]["deployments"])
        raw_vars = deepcopy(yaml_fixtures["config.runway.variables.yml"])
        deployment = DeploymentDefinition.from_list(raw_config)[0]
        raw_context = {"env_vars": os.environ.copy()}
        raw_context["env_vars"].update(ENV_VARS)
        deployment.resolve(
            MutableMap(**raw_context),
            variables=MutableMap(**raw_vars),
            pre_process=True,
        )

        # check resolved variables for pre_process
        assert deployment.account_id != 123456789101
        assert deployment.assume_role["arn"] == "arn:aws:iam::role/some-role"
        assert deployment.env_vars == {"MY_USERNAME": "test"}
        assert deployment.regions == ["us-east-1"]

        assert not deployment.parallel_regions, "not set in test config, should be None"

        # these should be unresolved at this point
        for attr in ["environments", "module_options"]:
            with pytest.raises(UnresolvedVariable):
                getattr(deployment, attr)

    def test_resolve(self, yaml_fixtures):
        """Test full resolution of variable attributes."""
        raw_config = deepcopy(yaml_fixtures["config.runway.yml"]["deployments"])
        raw_vars = deepcopy(yaml_fixtures["config.runway.variables.yml"])
        deployment = DeploymentDefinition.from_list(raw_config)[0]
        raw_context = {"env_vars": os.environ.copy()}
        raw_context["env_vars"].update(ENV_VARS)
        deployment.resolve(MutableMap(**raw_context), variables=MutableMap(**raw_vars))

        assert deployment.regions == ["us-east-1"]
        assert deployment.account_id != 123456789101
        assert deployment.assume_role["arn"] == "arn:aws:iam::role/some-role"
        assert deployment.env_vars == {"MY_USERNAME": "test"}
        assert deployment.environments == {
            "test_param": "lab value for ${envvar AWS_REGION}"
        }
        assert deployment.module_options == {
            "deployment_option": "test.deployment.module_options"
        }
        assert deployment.regions == ["us-east-1"]

        assert not deployment.parallel_regions, "not set in test config, should be None"


class TestFutureDefinition(object):
    """Test FutureDefinition."""

    def test_init(self, caplog):
        """Test init and the attributes it sets."""
        caplog.set_level(logging.INFO, logger="runway")
        config = {"strict_environments": True, "invalid_key": True}

        result = FutureDefinition(**config)
        assert result.strict_environments is config["strict_environments"]
        assert caplog.messages == [
            'invalid key(s) found in "future" have been ignored: invalid_key'
        ]

        with pytest.raises(TypeError):
            assert not FutureDefinition(strict_environments="true")
        assert not any(val for val in FutureDefinition().data.values())

    @pytest.mark.parametrize(
        "config, expected",
        [
            ({"strict_environments": True}, ["strict_environments"]),
            ({"strict_environments": False}, []),
        ],
    )
    def test_enabled(self, config, expected):
        """Tested enabled."""
        assert FutureDefinition(**config).enabled == expected


class TestModuleDefinition(object):
    """Test ModuleDefinition."""

    ATTRS = [
        "child_modules",
        "_class_path",
        "_env_vars",
        "_environments",
        "name",
        "_options",
        "_path",
        "tags",
    ]

    def test_from_list(self, yaml_fixtures):
        """Test init of a module from a list."""
        raw_config = deepcopy(
            yaml_fixtures["config.runway.yml"]["deployments"][0]["modules"][0]
        )
        module = ModuleDefinition.from_list(raw_config)[0]
        module_attrs = module.__dict__.keys()

        for attr in self.ATTRS:  # provides a better error than using all()
            assert attr in module_attrs

    def test_resolve(self, yaml_fixtures):
        """Test full resolution of variable attributes."""
        raw_config = deepcopy(
            yaml_fixtures["config.runway.yml"]["deployments"][0]["modules"]
        )
        raw_vars = deepcopy(yaml_fixtures["config.runway.variables.yml"])
        module = ModuleDefinition.from_list(raw_config)[0]
        raw_context = {"env_vars": os.environ.copy()}
        raw_context["env_vars"].update(ENV_VARS)
        module.resolve(MutableMap(**raw_context), variables=MutableMap(**raw_vars))

        assert module.child_modules == []
        assert not module.class_path
        assert module.env_vars == {"MY_USERNAME_MODULE": "test"}
        assert module.environments == {"module_test_param": "test"}
        assert module.name == "${var test_path}app.cfn"
        assert module.options == {"sample_module_option": "test.module.options"}
        assert module.path == "sampleapp.cfn"
        assert module.tags == {}


class TestTestDefinition(object):
    """Test TestDefinition."""

    ATTRS = ["_args", "name", "_required", "type"]

    def test_from_list(self, yaml_fixtures):
        """Test init of a deployment from a list."""
        raw_config = deepcopy(yaml_fixtures["config.runway.yml"]["tests"])
        test = ConfigTestDefinition.from_list(raw_config)[0]
        test_attrs = test.__dict__.keys()

        for attr in self.ATTRS:  # provides a better error than using all()
            assert attr in test_attrs

    def test_resolve(self, yaml_fixtures):
        """Test full resolution of variable attributes."""
        raw_config = deepcopy(yaml_fixtures["config.runway.yml"]["tests"])
        raw_vars = deepcopy(yaml_fixtures["config.runway.variables.yml"])
        test = ConfigTestDefinition.from_list(raw_config)[0]
        raw_context = {"env_vars": os.environ.copy()}
        raw_context["env_vars"].update(ENV_VARS)
        test.resolve(MutableMap(**raw_context), variables=MutableMap(**raw_vars))

        assert test.args == {"commands": ['echo "My name is test"']}
        assert test.name == "hello_world"
        assert isinstance(test.required, bool)
        assert test.required
        assert test.type == "script"


class TestVariablesDefinition(object):
    """Test VariablesDefinition."""

    def test_load(self, yaml_fixtures):
        """Test loading variables from a file with given path.

        Also tests setting variable from kwargs.

        """
        with NamedTemporaryFile(mode="w+", suffix=".yml") as var_file:
            var_file.write(yaml.safe_dump(yaml_fixtures["config.runway.variables.yml"]))
            var_file.seek(0)  # return curser to the top of the file
            result = VariablesDefinition.load(
                file_path=var_file.name, explicit_kwarg="not in file"
            )

            assert result.test_value == "basic value"
            assert result.explicit_kwarg == "not in file"

    def test_load_explicit_file_missing(self, caplog):
        """Test missing explicit file results in an error."""
        caplog.set_level("ERROR", logger="runway")

        with pytest.raises(SystemExit):
            VariablesDefinition.load(file_path="fake_file.yaml")

        assert caplog.records[0].msg == (
            'provided variables file "%s" ' "could not be found"
        )

    def test_load_no_file(self, caplog):
        """Should not error when default variables file is not found."""
        caplog.set_level("INFO", logger="runway")
        result = VariablesDefinition.load()

        assert result.data == {}
        assert caplog.records[0].msg == (
            "could not find %s in the current "
            "directory; continuing without a "
            "variables file"
        )
