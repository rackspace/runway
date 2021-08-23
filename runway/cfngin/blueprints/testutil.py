"""Provides a sublass of unittest.TestCase for testing blueprints."""
from __future__ import annotations

import difflib
import json
import os.path
import unittest
from glob import glob
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Type, cast

from ...config import CfnginConfig
from ...context import CfnginContext
from ...utils import load_object_from_string
from ...variables import Variable

if TYPE_CHECKING:
    from ...config.models.cfngin import CfnginStackDefinitionModel
    from .base import Blueprint


def diff(first: str, second: str) -> str:
    """Human readable differ."""
    return "\n".join(
        list(difflib.Differ().compare(first.splitlines(), second.splitlines()))
    )


class BlueprintTestCase(unittest.TestCase):
    """Extends the functionality of unittest.TestCase for testing blueprints."""

    OUTPUT_PATH: str = "tests/fixtures/blueprints"

    def assertRenderedBlueprint(  # noqa: N802 pylint: disable=invalid-name
        self, blueprint: Blueprint
    ) -> None:
        """Test that the rendered blueprint json matches the expected result.

        Result files are to be stored in the repo as
        ``test/fixtures/blueprints/${blueprint.name}.json``.

        """
        expected_output = f"{self.OUTPUT_PATH}/{blueprint.name}.json"

        rendered_dict = blueprint.template.to_dict()
        rendered_text = json.dumps(rendered_dict, indent=4, sort_keys=True)

        with open(
            expected_output + "-result", "w", encoding="utf-8"
        ) as expected_output_file:
            expected_output_file.write(rendered_text)

        with open(expected_output, encoding="utf-8") as expected_output_file:
            expected_dict = json.loads(expected_output_file.read())
            expected_text = json.dumps(expected_dict, indent=4, sort_keys=True)

        self.assertEqual(
            rendered_dict, expected_dict, diff(rendered_text, expected_text)
        )


class YamlDirTestGenerator:
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

    def __init__(self) -> None:
        """Instantiate class."""
        self.classdir = os.path.relpath(self.__class__.__module__.replace(".", "/"))
        if not os.path.isdir(self.classdir):
            self.classdir = os.path.dirname(self.classdir)

    # These properties can be overridden from the test generator subclass.
    @property
    def base_class(self) -> Type[BlueprintTestCase]:
        """Return the baseclass."""
        return BlueprintTestCase

    @property
    def yaml_dirs(self) -> List[str]:
        """Yaml directories."""
        return ["."]

    @property
    def yaml_filename(self) -> str:
        """Yaml filename."""
        return "test_*.yaml"

    # pylint incorrectly detects this
    def test_generator(  # pylint: disable=no-self-use
        self,
    ) -> Iterator[BlueprintTestCase]:
        """Test generator."""
        # Search for tests in given paths
        configs: List[str] = []
        for directory in self.yaml_dirs:
            configs.extend(glob(f"{self.classdir}/{directory}/{self.yaml_filename}"))

        class ConfigTest(self.base_class):  # type: ignore
            """Config test."""

            context: CfnginContext

            def __init__(  # pylint: disable=super-init-not-called
                self,
                config: CfnginConfig,
                stack: CfnginStackDefinitionModel,
                filepath: Path,
            ) -> None:
                """Instantiate class."""
                self.config = config
                self.stack = stack
                self.description = f"{stack.name} ({filepath})"

            def __call__(self) -> None:  # pylint: disable=arguments-differ
                """Run when the class instance is called directly."""
                # Use the context property of the baseclass, if present.
                # If not, default to a basic context.
                try:
                    ctx = self.context
                except AttributeError:
                    ctx = CfnginContext(
                        config=self.config, parameters={"environment": "test"}
                    )

                configvars = self.stack.variables or {}
                variables = [Variable(k, v, "cfngin") for k, v in configvars.items()]

                blueprint_class = load_object_from_string(
                    cast(str, self.stack.class_path)
                )
                blueprint = blueprint_class(self.stack.name, ctx)
                blueprint.resolve_variables(variables or [])
                blueprint.setup_parameters()
                blueprint.create_template()
                self.assertRenderedBlueprint(blueprint)

            def assertEqual(  # noqa pylint: disable=invalid-name
                self, first: Any, second: Any, msg: Optional[str] = None
            ) -> None:
                """Test that first and second are equal.

                If the values do not compare equal, the test will fail.

                """
                assert first == second, msg

        for config_file in configs:
            config_path = Path(config_file)
            config = CfnginConfig.parse_file(file_path=config_path)
            for stack in config.stacks:
                # Nosetests supports "test generators", which allows us to
                # yield a callable object which will be wrapped as a test
                # case.
                #
                # http://nose.readthedocs.io/en/latest/writing_tests.html#test-generators
                yield ConfigTest(config, stack, filepath=config_path)
