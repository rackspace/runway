"""Test Runway config classes."""
import os
from copy import deepcopy
from tempfile import NamedTemporaryFile

import pytest
import yaml

from runway.cfngin.exceptions import UnresolvedVariable
from runway.config import DeploymentDefinition, ModuleDefinition
# tries to test the imported class unless using "as"
from runway.config import TestDefinition as ConfigTestDefinition
from runway.config import VariablesDefinition
from runway.util import MutableMap

YAML_FIXTURES = ['config.runway.yml', 'config.runway.variables.yml']
ENV_VARS = {
    'AWS_REGION': 'us-east-1',
    'DEPLOY_ENVIRONMENT': 'test',
    'USER': 'test'
}


class TestDeploymentDefinition(object):
    """Test DeploymentDefinition."""

    ATTRS = ['_account_alias', '_account_id', '_assume_role',
             '_env_vars', '_environments', '_module_options', 'modules',
             'name', '_regions', '_parallel_regions']

    def test_from_list(self, yaml_fixtures):
        """Test init of a deployment from a list."""
        raw_config = deepcopy(yaml_fixtures['config.runway.yml']['deployments'])
        deployment = DeploymentDefinition.from_list(raw_config)[0]
        deployment_attrs = deployment.__dict__.keys()

        assert deployment.name == 'deployment_1'

        for attr in self.ATTRS:  # provides a better error than using all()
            assert attr in deployment_attrs

    def test_pre_process_resolve(self, yaml_fixtures):
        """Test that pre-process resolution only resolves specific vars."""
        raw_config = deepcopy(yaml_fixtures['config.runway.yml']['deployments'])
        raw_vars = deepcopy(yaml_fixtures['config.runway.variables.yml'])
        deployment = DeploymentDefinition.from_list(raw_config)[0]
        raw_context = {'env_vars': os.environ.copy()}
        raw_context['env_vars'].update(ENV_VARS)
        deployment.resolve(MutableMap(**raw_context),
                           variables=MutableMap(**raw_vars),
                           pre_process=True)

        # check resolved variables for pre_process
        assert not deployment.account_id == 123456789101
        assert deployment.assume_role['arn'] == 'arn:aws:iam::role/some-role'
        assert deployment.env_vars == {'MY_USERNAME': 'test'}
        assert deployment.regions == ['us-east-1']

        assert not deployment.parallel_regions, 'not set in test config, should be None'

        # these should be unresolved at this point
        for attr in ['environments', 'module_options']:
            with pytest.raises(UnresolvedVariable):
                getattr(deployment, attr)

    def test_resolve(self, yaml_fixtures):
        """Test full resolution of variable attributes."""
        raw_config = deepcopy(yaml_fixtures['config.runway.yml']['deployments'])
        raw_vars = deepcopy(yaml_fixtures['config.runway.variables.yml'])
        deployment = DeploymentDefinition.from_list(raw_config)[0]
        raw_context = {'env_vars': os.environ.copy()}
        raw_context['env_vars'].update(ENV_VARS)
        deployment.resolve(MutableMap(**raw_context),
                           variables=MutableMap(**raw_vars))

        assert deployment.regions == ['us-east-1']
        assert not deployment.account_id == 123456789101
        assert deployment.assume_role['arn'] == 'arn:aws:iam::role/some-role'
        assert deployment.env_vars == {'MY_USERNAME': 'test'}
        assert deployment.environments == {
            'test_param': 'lab value for ${envvar AWS_REGION}'
        }
        assert deployment.module_options == {
            'deployment_option': 'test.deployment.module_options'
        }
        assert deployment.regions == ['us-east-1']

        assert not deployment.parallel_regions, 'not set in test config, should be None'


class TestModuleDefinition(object):
    """Test ModuleDefinition."""

    ATTRS = ['child_modules', '_class_path', '_env_vars', '_environments',
             'name', '_options', '_path', 'tags']

    def test_from_list(self, yaml_fixtures):
        """Test init of a module from a list."""
        raw_config = deepcopy(
            yaml_fixtures['config.runway.yml']['deployments'][0]['modules'][0]
        )
        module = ModuleDefinition.from_list(raw_config)[0]
        module_attrs = module.__dict__.keys()

        for attr in self.ATTRS:  # provides a better error than using all()
            assert attr in module_attrs

    def test_resolve(self, yaml_fixtures):
        """Test full resolution of variable attributes."""
        raw_config = deepcopy(
            yaml_fixtures['config.runway.yml']['deployments'][0]['modules']
        )
        raw_vars = deepcopy(yaml_fixtures['config.runway.variables.yml'])
        module = ModuleDefinition.from_list(raw_config)[0]
        raw_context = {'env_vars': os.environ.copy()}
        raw_context['env_vars'].update(ENV_VARS)
        module.resolve(MutableMap(**raw_context),
                       variables=MutableMap(**raw_vars))

        assert module.child_modules == []
        assert not module.class_path
        assert module.env_vars == {'MY_USERNAME_MODULE': 'test'}
        assert module.environments == {'module_test_param': 'test'}
        assert module.name == '${var test_path}app.cfn'
        assert module.options == {'sample_module_option': 'test.module.options'}
        assert module.path == 'sampleapp.cfn'
        assert module.tags == {}


class TestTestDefinition(object):
    """Test TestDefinition."""

    ATTRS = ['_args', 'name', '_required', 'type']

    def test_from_list(self, yaml_fixtures):
        """Test init of a deployment from a list."""
        raw_config = deepcopy(yaml_fixtures['config.runway.yml']['tests'])
        test = ConfigTestDefinition.from_list(raw_config)[0]
        test_attrs = test.__dict__.keys()

        for attr in self.ATTRS:  # provides a better error than using all()
            assert attr in test_attrs

    def test_resolve(self, yaml_fixtures):
        """Test full resolution of variable attributes."""
        raw_config = deepcopy(yaml_fixtures['config.runway.yml']['tests'])
        raw_vars = deepcopy(yaml_fixtures['config.runway.variables.yml'])
        test = ConfigTestDefinition.from_list(raw_config)[0]
        raw_context = {'env_vars': os.environ.copy()}
        raw_context['env_vars'].update(ENV_VARS)
        test.resolve(MutableMap(**raw_context),
                     variables=MutableMap(**raw_vars))

        assert test.args == {'commands': ['echo "My name is test"']}
        assert test.name == 'hello_world'
        assert isinstance(test.required, bool)
        assert test.required
        assert test.type == 'script'


class TestVariablesDefinition(object):
    """Test VariablesDefinition."""

    def test_load(self, yaml_fixtures):
        """Test loading variables from a file with given path.

        Also tests setting variable from kwargs.

        """
        with NamedTemporaryFile(mode='w+', suffix='.yml') as var_file:
            var_file.write(
                yaml.safe_dump(yaml_fixtures['config.runway.variables.yml'])
            )
            var_file.seek(0)  # return curser to the top of the file
            result = VariablesDefinition.load(
                file_path=var_file.name, explicit_kwarg='not in file'
            )

            assert result.test_value == 'basic value'
            assert result.explicit_kwarg == 'not in file'

    def test_load_explicit_file_missing(self, caplog):
        """Test missing explicit file results in an error."""
        caplog.set_level('ERROR', logger='runway')

        with pytest.raises(SystemExit):
            VariablesDefinition.load(file_path='fake_file.yaml')

        assert caplog.records[0].msg == ('The provided variables "%s" file '
                                         'could not be found.')

    def test_load_no_file(self, caplog):
        """Should not error when default variables file is not found."""
        caplog.set_level('INFO', logger='runway')
        result = VariablesDefinition.load()

        assert result.data == {}
        assert caplog.records[0].msg == ('Could not find %s in the current '
                                         'directory. Continuing without a '
                                         'variables file.')
