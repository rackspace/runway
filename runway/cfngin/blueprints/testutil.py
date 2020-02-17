"""Provides a sublass of unittest.TestCase for testing blueprints."""
import difflib
import json
import os.path
import unittest
from glob import glob

from runway.util import load_object_from_string
from runway.variables import Variable

from ..config import parse as parse_config
from ..context import Context


def diff(first, second):
    """Human readable differ."""
    return '\n'.join(
        list(
            difflib.Differ().compare(
                first.splitlines(),
                second.splitlines()
            )
        )
    )


class BlueprintTestCase(unittest.TestCase):
    """Extends the functionality of unittest.TestCase for testing blueprints."""

    OUTPUT_PATH = "tests/fixtures/blueprints"

    def assertRenderedBlueprint(self, blueprint):  # noqa: N802 pylint: disable=invalid-name
        """Test that the rendered blueprint json matches the expected result.

        Result files are to be stored in the repo as
        ``test/fixtures/blueprints/${blueprint.name}.json``.

        """
        expected_output = "%s/%s.json" % (self.OUTPUT_PATH, blueprint.name)

        rendered_dict = blueprint.template.to_dict()
        rendered_text = json.dumps(rendered_dict, indent=4, sort_keys=True)

        with open(expected_output + "-result", "w") as expected_output_file:
            expected_output_file.write(rendered_text)

        with open(expected_output) as expected_output_file:
            expected_dict = json.loads(expected_output_file.read())
            expected_text = json.dumps(expected_dict, indent=4, sort_keys=True)

        self.assertEqual(rendered_dict, expected_dict,
                         diff(rendered_text, expected_text))


class YamlDirTestGenerator(object):
    """Generate blueprint tests from yaml config files.

    This class creates blueprint tests from yaml files with a syntax similar
    to CFNgin configuration syntax. For example::

        namespace: test
        stacks:
            - name: test_sample
            class_path: blueprints.test.Sample
            variables:
                var1: value1

    Will create a test for the specified blueprint, passing that variable as
    part of the test.

    The test will generate a ``.json`` file for this blueprint, and compare it
    with the stored result.

    By default, the generator looks for files named ``test_*.yaml`` in its same
    directory. In order to use it, subclass it in a directory containing such
    tests, and name the class with a pattern that will include it in nosetests'
    tests (for example, TestGenerator).

    The subclass may override some ``@property`` definitions:

    **base_class**
      By default, the generated tests are subclasses or
      :class:`runway.cfngin.blueprints.testutil.BlueprintTestCase`. In order
      to change this, set this property to the desired base class.

    **yaml_dirs:**
      By default, the directory where the generator is subclassed is searched
      for test files. Override this array for specifying more directories.
      These must be relative to the directory in which the subclass lives in.
      Globs may be used. Default: ``['.']``.
      Example override: ``['.', 'tests/*/']``

    **yaml_filename:**
      By default, the generator looks for files named ``test_*.yaml``.
      Use this to change this pattern. Globs may be used.

    """

    def __init__(self):
        """Instantiate class."""
        self.classdir = os.path.relpath(
            self.__class__.__module__.replace('.', '/'))
        if not os.path.isdir(self.classdir):
            self.classdir = os.path.dirname(self.classdir)

    # These properties can be overridden from the test generator subclass.
    @property
    def base_class(self):
        """Return the baseclass."""
        return BlueprintTestCase

    @property
    def yaml_dirs(self):
        """Yaml directories."""
        return ['.']

    @property
    def yaml_filename(self):
        """Yaml filename."""
        return 'test_*.yaml'

    # pylint incorrectly detects this
    def test_generator(self):  # pylint: disable=no-self-use
        """Test generator."""
        # Search for tests in given paths
        configs = []
        for directory in self.yaml_dirs:
            configs.extend(
                glob('%s/%s/%s' % (self.classdir, directory,
                                   self.yaml_filename)))

        class ConfigTest(self.base_class):
            """Config test."""

            def __init__(self, config, stack, filepath):  # pylint: disable=super-init-not-called
                """Instantiate class."""
                self.config = config
                self.stack = stack
                self.description = "%s (%s)" % (stack.name, filepath)

            def __call__(self):  # pylint: disable=arguments-differ
                """Run when the class instance is called directly."""
                # Use the context property of the baseclass, if present.
                # If not, default to a basic context.
                try:
                    ctx = self.context
                except AttributeError:
                    ctx = Context(config=self.config,
                                  environment={'environment': 'test'})

                configvars = self.stack.variables or {}
                variables = [Variable(k, v, 'cfngin')
                             for k, v in configvars.iteritems()]

                blueprint_class = load_object_from_string(
                    self.stack.class_path)
                blueprint = blueprint_class(self.stack.name, ctx)
                blueprint.resolve_variables(variables or [])
                blueprint.setup_parameters()
                blueprint.create_template()
                self.assertRenderedBlueprint(blueprint)

            def assertEqual(self, first, second, msg=None):  # noqa pylint: disable=invalid-name
                """Test that first and second are equal.

                If the values do not compare equal, the test will fail.

                """
                assert first == second, msg

        for config_file in configs:
            with open(config_file) as test:
                config = parse_config(test.read())
                config.validate()

                for stack in config.stacks:  # pylint: disable=not-an-iterable
                    # Nosetests supports "test generators", which allows us to
                    # yield a callable object which will be wrapped as a test
                    # case.
                    #
                    # http://nose.readthedocs.io/en/latest/writing_tests.html#test-generators
                    yield ConfigTest(config, stack, filepath=config_file)
