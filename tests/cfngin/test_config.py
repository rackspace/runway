"""Tests for runway.cfngin.config."""
# pylint: disable=no-member
import sys
import unittest

from yaml.constructor import ConstructorError

from runway.cfngin import exceptions
from runway.cfngin.config import (Config, Stack, dump, load, parse,
                                  process_remote_sources, render,
                                  render_parse_load)
from runway.cfngin.environment import parse_environment
from runway.cfngin.lookups.registry import CFNGIN_LOOKUP_HANDLERS

CONFIG = """a: $a
b: $b
c: $c"""


class TestConfig(unittest.TestCase):
    """Tests for runway.cfngin.config."""

    def test_render_missing_env(self):
        """Test render missing env."""
        env = {"a": "A"}
        with self.assertRaises(exceptions.MissingEnvironment) as expected:
            render(CONFIG, env)
        self.assertEqual(expected.exception.key, "b")

    def test_render_no_variable_config(self):
        """Test render no variable config."""
        config = render("namespace: prod", {})
        self.assertEqual("namespace: prod", config)

    def test_render_valid_env_substitution(self):
        """Test render valid env substitution."""
        config = render("namespace: $namespace", {"namespace": "prod"})
        self.assertEqual("namespace: prod", config)

    def test_render_blank_env_values(self):
        """Test ender blank env values."""
        conf = """namespace: ${namespace}"""
        env = parse_environment("""namespace:""")
        config = render(conf, env)
        self.assertEqual("namespace: ", config)
        env = parse_environment("""namespace: !!str""")
        config = render(conf, env)
        self.assertEqual("namespace: !!str", config)

    def test_config_validate_missing_stack_source(self):
        """Test config validate missing stack source."""
        config = Config({
            "namespace": "prod",
            "stacks": [
                {
                    "name": "bastion"}]})
        with self.assertRaises(exceptions.InvalidConfig) as ex:
            config.validate()

        stack_errors = ex.exception.errors['stacks'][0]
        assert stack_errors['template_path'][0].__str__() == \
            "class_path or template_path is required."
        assert stack_errors['class_path'][0].__str__() == \
            "class_path or template_path is required."

    def test_config_validate_missing_stack_source_when_locked(self):
        """Test config validate missing stack source when locked."""
        config = Config({
            "namespace": "prod",
            "stacks": [
                {
                    "name": "bastion",
                    "locked": True}]})
        config.validate()

    def test_config_validate_stack_class_and_template_paths(self):
        """Test config validate stack class and template paths."""
        config = Config({
            "namespace": "prod",
            "stacks": [
                {
                    "name": "bastion",
                    "class_path": "foo",
                    "template_path": "bar"}]})
        with self.assertRaises(exceptions.InvalidConfig) as ex:
            config.validate()

        stack_errors = ex.exception.errors['stacks'][0]
        assert stack_errors['template_path'][0].__str__() == \
            "class_path cannot be present when template_path is provided."
        assert stack_errors['class_path'][0].__str__() == \
            "template_path cannot be present when class_path is provided."

    def test_config_validate_missing_name(self):
        """Test config validate missing name."""
        config = Config({
            "namespace": "prod",
            "stacks": [
                {
                    "class_path": "blueprints.Bastion"}]})
        with self.assertRaises(exceptions.InvalidConfig) as ex:
            config.validate()

        error = ex.exception.errors['stacks'][0]['name'].errors[0]
        assert error.__str__() == "This field is required."

    def test_config_validate_duplicate_stack_names(self):
        """Test config validate duplicate stack names."""
        config = Config({
            "namespace": "prod",
            "stacks": [
                {
                    "name": "bastion",
                    "class_path": "blueprints.Bastion"},
                {
                    "name": "bastion",
                    "class_path": "blueprints.BastionV2"}]})
        with self.assertRaises(exceptions.InvalidConfig) as ex:
            config.validate()

        error = ex.exception.errors['stacks'][0]
        assert error.__str__() == "Duplicate stack bastion found at index 0."

    def test_dump_unicode(self):
        """Test dump unicode."""
        config = Config()
        config.namespace = "test"
        assert dump(config) == b"""namespace: test
stacks: []
"""

        config = Config({"namespace": "test"})
        # Ensure that we're producing standard yaml, that doesn't include
        # python specific objects.
        assert dump(config) != b"namespace: !!python/unicode 'test'\n"
        assert dump(config) == b"""namespace: test
stacks: []
"""

    def test_parse_tags(self):
        """Test parse tags."""
        config = parse("""
        namespace: prod
        tags:
          "a:b": "c"
          "hello": 1
          simple_tag: simple value
        """)
        assert config.tags == {
            "a:b": "c",
            "hello": "1",
            "simple_tag": "simple value"
        }

    def test_parse_with_arbitrary_anchors(self):
        """Test parse with arbitrary anchors."""
        config = parse("""
        namespace: prod
        common_variables: &common_variables
          Foo: bar
        stacks:
        - name: vpc
          class_path: blueprints.VPC
          variables:
            << : *common_variables
        """)

        stack = config.stacks[0]
        assert stack.variables == {"Foo": "bar"}

    def test_parse_with_deprecated_parameters(self):
        """Test parse with deprecated parameters."""
        config = parse("""
        namespace: prod
        stacks:
        - name: vpc
          class_path: blueprints.VPC
          parameters:
            Foo: bar
        """)
        with self.assertRaises(exceptions.InvalidConfig) as ex:
            config.validate()

        error = ex.exception.errors['stacks'][0]['parameters'][0]
        assert error.__str__() == (
            "DEPRECATION: Stack definition vpc contains deprecated 'parameters'"
            ", rather than 'variables'. You are required to update your config. "
            "See https://docs.onica.com/projects/runway/en/release/cfngin/config.html#variables "
            "for additional information."
        )

    def test_config_build(self):
        """Test config build."""
        vpc = Stack({"name": "vpc", "class_path": "blueprints.VPC"})
        config = Config({"namespace": "prod", "stacks": [vpc]})
        assert config.namespace == 'prod'
        assert config.stacks[0].name == 'vpc'
        assert config["namespace"] == 'prod'
        config.validate()

    def test_parse(self):
        """Test parse."""
        config_with_lists = """
        namespace: prod
        stacker_bucket: cfngin-prod
        pre_build:
          - path: runway.cfngin.hooks.route53.create_domain
            required: true
            enabled: true
            args:
              domain: mydomain.com
        post_build:
          - path: runway.cfngin.hooks.route53.create_domain
            required: true
            enabled: true
            args:
              domain: mydomain.com
        pre_destroy:
          - path: runway.cfngin.hooks.route53.create_domain
            required: true
            enabled: true
            args:
              domain: mydomain.com
        post_destroy:
          - path: runway.cfngin.hooks.route53.create_domain
            required: true
            enabled: true
            args:
              domain: mydomain.com
        package_sources:
          s3:
            - bucket: acmecorpbucket
              key: public/acmecorp-blueprints-v1.zip
            - bucket: examplecorpbucket
              key: public/examplecorp-blueprints-v2.tar.gz
              requester_pays: true
            - bucket: anotherexamplebucket
              key: example-blueprints-v3.tar.gz
              use_latest: false
              paths:
                - foo
              configs:
                - foo/config.yml
          git:
            - uri: git@github.com:acmecorp/stacker_blueprints.git
            - uri: git@github.com:remind101/stacker_blueprints.git
              tag: 1.0.0
              paths:
                - stacker_blueprints
            - uri: git@github.com:contoso/webapp.git
              branch: staging
            - uri: git@github.com:contoso/foo.git
              commit: 12345678
              paths:
                - bar
              configs:
                - bar/moreconfig.yml
        tags:
          environment: production
        stacks:
        - name: vpc
          class_path: blueprints.VPC
          variables:
            PrivateSubnets:
            - 10.0.0.0/24
        - name: bastion
          class_path: blueprints.Bastion
          requires: ['vpc']
          variables:
            VpcId: ${output vpc::VpcId}
        """
        config_with_dicts = """
        namespace: prod
        stacker_bucket: cfngin-prod
        pre_build:
          prebuild_createdomain:
            path: runway.cfngin.hooks.route53.create_domain
            required: true
            enabled: true
            args:
              domain: mydomain.com
        post_build:
          postbuild_createdomain:
            path: runway.cfngin.hooks.route53.create_domain
            required: true
            enabled: true
            args:
              domain: mydomain.com
        pre_destroy:
          predestroy_createdomain:
            path: runway.cfngin.hooks.route53.create_domain
            required: true
            enabled: true
            args:
              domain: mydomain.com
        post_destroy:
          postdestroy_createdomain:
            path: runway.cfngin.hooks.route53.create_domain
            required: true
            enabled: true
            args:
              domain: mydomain.com
        package_sources:
          s3:
            - bucket: acmecorpbucket
              key: public/acmecorp-blueprints-v1.zip
            - bucket: examplecorpbucket
              key: public/examplecorp-blueprints-v2.tar.gz
              requester_pays: true
            - bucket: anotherexamplebucket
              key: example-blueprints-v3.tar.gz
              use_latest: false
              paths:
                - foo
              configs:
                - foo/config.yml
          git:
            - uri: git@github.com:acmecorp/stacker_blueprints.git
            - uri: git@github.com:remind101/stacker_blueprints.git
              tag: 1.0.0
              paths:
                - stacker_blueprints
            - uri: git@github.com:contoso/webapp.git
              branch: staging
            - uri: git@github.com:contoso/foo.git
              commit: 12345678
              paths:
                - bar
              configs:
                - bar/moreconfig.yml
        tags:
          environment: production
        stacks:
          vpc:
            class_path: blueprints.VPC
            variables:
              PrivateSubnets:
              - 10.0.0.0/24
          bastion:
            class_path: blueprints.Bastion
            requires: ['vpc']
            variables:
              VpcId: ${output vpc::VpcId}
        """

        for raw_config in [config_with_lists, config_with_dicts]:
            config = parse(raw_config)

            config.validate()

            assert config.namespace == 'prod'
            assert config.stacker_bucket == 'cfngin-prod'

            for hooks in [config.pre_build, config.post_build,
                          config.pre_destroy, config.post_destroy]:
                assert hooks[0].path == 'runway.cfngin.hooks.route53.create_domain'
                assert hooks[0].required
                assert hooks[0].args == {"domain": "mydomain.com"}

            assert config.package_sources.s3[0].bucket == 'acmecorpbucket'
            assert config.package_sources.s3[0].key == \
                'public/acmecorp-blueprints-v1.zip'
            assert config.package_sources.s3[1].bucket == 'examplecorpbucket'
            assert config.package_sources.s3[1].key == \
                'public/examplecorp-blueprints-v2.tar.gz'
            assert config.package_sources.s3[1].requester_pays
            assert not config.package_sources.s3[2].use_latest

            assert config.package_sources.git[0].uri == \
                'git@github.com:acmecorp/stacker_blueprints.git'
            assert config.package_sources.git[1].uri == \
                'git@github.com:remind101/stacker_blueprints.git'
            assert config.package_sources.git[1].tag == '1.0.0'
            assert config.package_sources.git[1].paths == ['stacker_blueprints']
            assert config.package_sources.git[2].branch == 'staging'

            assert config.tags == {"environment": "production"}

            assert len(config.stacks) == 2
            self.assertEqual(len(config.stacks), 2)

            vpc_index = next(
                i for (i, d) in enumerate(config.stacks) if d.name == 'vpc'
            )
            vpc = config.stacks[vpc_index]
            self.assertEqual(vpc.name, "vpc")
            self.assertEqual(vpc.class_path, "blueprints.VPC")
            self.assertEqual(vpc.requires, None)
            self.assertEqual(vpc.variables,
                             {"PrivateSubnets": ["10.0.0.0/24"]})

            bastion_index = next(
                i for (i, d) in enumerate(config.stacks) if d.name == "bastion"
            )
            bastion = config.stacks[bastion_index]
            self.assertEqual(bastion.name, "bastion")
            self.assertEqual(bastion.class_path, "blueprints.Bastion")
            self.assertEqual(bastion.requires, ["vpc"])
            self.assertEqual(bastion.variables,
                             {"VpcId": "${output vpc::VpcId}"})

    def test_dump_complex(self):
        """Test dump complex."""
        config = Config({
            "namespace": "prod",
            "stacks": [
                Stack({
                    "name": "vpc",
                    "class_path": "blueprints.VPC"}),
                Stack({
                    "name": "bastion",
                    "class_path": "blueprints.Bastion",
                    "requires": ["vpc"]})]})

        self.assertEqual(dump(config), b"""namespace: prod
stacks:
- class_path: blueprints.VPC
  enabled: true
  locked: false
  name: vpc
  protected: false
  termination_protection: false
- class_path: blueprints.Bastion
  enabled: true
  locked: false
  name: bastion
  protected: false
  requires:
  - vpc
  termination_protection: false
""")

    def test_load_register_custom_lookups(self):
        """Test load register custom lookups."""
        config = Config({
            "lookups": {
                "custom": "importlib.import_module"}})
        load(config)
        self.assertTrue(callable(CFNGIN_LOOKUP_HANDLERS["custom"]))

    def test_load_adds_sys_path(self):
        """Test load adds sys path."""
        config = Config({"sys_path": "/foo/bar"})
        load(config)
        self.assertIn("/foo/bar", sys.path)

    def test_process_empty_remote_sources(self):
        """Test process empty remote sources."""
        config = """
        namespace: prod
        stacks:
          - name: vpc
            class_path: blueprints.VPC
        """
        self.assertEqual(config, process_remote_sources(config))

    def test_lookup_with_sys_path(self):
        """Test lookup with sys path."""
        config = Config({
            "sys_path": "./tests/cfngin",
            "lookups": {
                "custom": "fixtures.mock_lookups.handler"}})
        load(config)
        self.assertTrue(callable(CFNGIN_LOOKUP_HANDLERS["custom"]))

    def test_render_parse_load_namespace_fallback(self):
        """Test render parse load namespace fallback."""
        conf = """
        stacks:
        - name: vpc
          class_path: blueprints.VPC
        """
        config = render_parse_load(
            conf, environment={"namespace": "prod"}, validate=False)
        config.validate()
        assert config.namespace == 'prod'

    def test_allow_most_keys_to_be_duplicates_for_overrides(self):
        """Test allow most keys to be duplicates for overrides."""
        yaml_config = """
        namespace: prod
        stacks:
          - name: vpc
            class_path: blueprints.VPC
            variables:
              CIDR: 192.168.1.0/24
              CIDR: 192.168.2.0/24
        """
        doc = parse(yaml_config)
        print(doc.to_primitive())
        self.assertEqual(
            doc["stacks"][0]["variables"]["CIDR"], "192.168.2.0/24"
        )
        yaml_config = """
        default_variables: &default_variables
          CIDR: 192.168.1.0/24
        namespace: prod
        stacks:
          - name: vpc
            class_path: blueprints.VPC
            variables:
              << : *default_variables
              CIDR: 192.168.2.0/24
        """
        doc = parse(yaml_config)
        self.assertEqual(
            doc["stacks"][0]["variables"]["CIDR"], "192.168.2.0/24"
        )

    def test_raise_constructor_error_on_keyword_duplicate_key(self):
        """Some keys should never have a duplicate sibling.

        For example we treat `class_path` as a special "keyword" and
        disallow dupes.

        """
        yaml_config = """
        namespace: prod
        stacks:
          - name: vpc
            class_path: blueprints.VPC
            class_path: blueprints.Fake
        """
        with self.assertRaises(ConstructorError):
            parse(yaml_config)

    def test_raise_construct_error_on_duplicate_stack_name_dict(self):
        """Some mappings should never have a duplicate children.

        For example we treat `stacks` as a special mapping and disallow
        dupe children keys.

        """
        yaml_config = """
        namespace: prod
        stacks:
          my_vpc:
            class_path: blueprints.VPC1
          my_vpc:
            class_path: blueprints.VPC2
        """
        with self.assertRaises(ConstructorError):
            parse(yaml_config)

    def test_parse_invalid_inner_keys(self):
        """Test parse invalid innerkeys."""
        yaml_config = """
        namespace: prod
        stacks:
        - name: vpc
          class_path: blueprints.VPC
          garbage: yes
          variables:
            Foo: bar
        """

        with self.assertRaises(exceptions.InvalidConfig):
            parse(yaml_config)

    def test_stacker_to_runway_field_conversion(self):
        """Ensure the correct value is being presented by the config."""
        yaml_config = """
        namespace: test
        cfngin_bucket: ''
        stacker_bucket: test-bucket
        cfngin_bucket_region: us-east-1
        stacker_cache_dir: ./test/path
        """
        config = parse(yaml_config)
        # config.validate()

        assert config.cfngin_bucket == ''
        assert config.cfngin_bucket_region == 'us-east-1'
        assert config.cfngin_cache_dir == './test/path'


if __name__ == '__main__':
    unittest.main()
