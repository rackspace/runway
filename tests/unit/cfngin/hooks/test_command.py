"""Tests for runway.cfngin.hooks.command."""
import os
import unittest
from subprocess import PIPE

import mock

from runway.cfngin.config import Config
from runway.cfngin.context import Context
from runway.cfngin.hooks.command import run_command

from ..factories import mock_provider


class MockProcess(object):
    """Mock process."""

    def __init__(self, returncode=0, stdout='', stderr=''):
        """Instantiate class."""
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.stdin = None

    def communicate(self, stdin):
        """Communicate with process."""
        self.stdin = stdin
        return (self.stdout, self.stderr)

    def wait(self):
        """Wait for process."""
        return self.returncode

    def kill(self):
        """Kill process."""
        return


class TestCommandHook(unittest.TestCase):
    """Tests for runway.cfngin.hooks.command."""

    def setUp(self):
        """Run before tests."""
        self.context = Context(
            config=Config({'namespace': 'test', 'stacker_bucket': 'test'}))
        self.provider = mock_provider(region="us-east-1")

        self.mock_process = MockProcess()
        self.popen_mock = \
            mock.patch('runway.cfngin.hooks.command.Popen',
                       return_value=self.mock_process).start()

        self.devnull = mock.Mock()
        self.devnull_mock = \
            mock.patch('runway.cfngin.hooks.command._devnull',
                       return_value=self.devnull).start()

    def tearDown(self):
        """Run after tests."""
        self.devnull_mock.stop()
        self.popen_mock.stop()

    def run_hook(self, **kwargs):
        """Run hook."""
        real_kwargs = {
            'context': self.context,
            'provider': self.provider,
        }
        real_kwargs.update(kwargs)

        return run_command(**real_kwargs)

    def test_command_ok(self):
        """Test command ok."""
        self.mock_process.returncode = 0
        self.mock_process.stdout = None
        self.mock_process.stderr = None

        results = self.run_hook(command=['foo'])

        self.assertEqual(
            results, {'returncode': 0, 'stdout': None, 'stderr': None})
        self.popen_mock.assert_called_once_with(
            ['foo'], stdin=self.devnull, stdout=None, stderr=None, env=None)

    def test_command_fail(self):
        """Test command fail."""
        self.mock_process.returncode = 1
        self.mock_process.stdout = None
        self.mock_process.stderr = None

        results = self.run_hook(command=['foo'])

        self.assertEqual(results, None)
        self.popen_mock.assert_called_once_with(
            ['foo'], stdin=self.devnull, stdout=None, stderr=None, env=None)

    def test_command_ignore_status(self):
        """Test command ignore status."""
        self.mock_process.returncode = 1
        self.mock_process.stdout = None
        self.mock_process.stderr = None

        results = self.run_hook(command=['foo'], ignore_status=True)

        self.assertEqual(
            results, {'returncode': 1, 'stdout': None, 'stderr': None})
        self.popen_mock.assert_called_once_with(
            ['foo'], stdin=self.devnull, stdout=None, stderr=None, env=None)

    def test_command_quiet(self):
        """Test command quiet."""
        self.mock_process.returncode = 0
        self.mock_process.stdout = None
        self.mock_process.stderr = None

        results = self.run_hook(command=['foo'], quiet=True)
        self.assertEqual(
            results, {'returncode': 0, 'stdout': None, 'stderr': None})

        self.popen_mock.assert_called_once_with(
            ['foo'], stdin=self.devnull, stdout=self.devnull,
            stderr=self.devnull, env=None)

    def test_command_interactive(self):
        """Test command interactive."""
        self.mock_process.returncode = 0
        self.mock_process.stdout = None
        self.mock_process.stderr = None

        results = self.run_hook(command=['foo'], interactive=True)
        self.assertEqual(
            results, {'returncode': 0, 'stdout': None, 'stderr': None})

        self.popen_mock.assert_called_once_with(
            ['foo'], stdin=None, stdout=None, stderr=None, env=None)

    def test_command_input(self):
        """Test command input."""
        self.mock_process.returncode = 0
        self.mock_process.stdout = None
        self.mock_process.stderr = None

        results = self.run_hook(command=['foo'], stdin='hello world')
        self.assertEqual(
            results, {'returncode': 0, 'stdout': None, 'stderr': None})

        self.popen_mock.assert_called_once_with(
            ['foo'], stdin=PIPE, stdout=None, stderr=None, env=None)
        self.assertEqual(self.mock_process.stdin, 'hello world')

    def test_command_capture(self):
        """Test command capture."""
        self.mock_process.returncode = 0
        self.mock_process.stdout = 'hello'
        self.mock_process.stderr = 'world'

        results = self.run_hook(command=['foo'], capture=True)
        self.assertEqual(
            results, {'returncode': 0, 'stdout': 'hello', 'stderr': 'world'})

        self.popen_mock.assert_called_once_with(
            ['foo'], stdin=self.devnull, stdout=PIPE, stderr=PIPE, env=None)

    def test_command_env(self):
        """Test command env."""
        self.mock_process.returncode = 0
        self.mock_process.stdout = None
        self.mock_process.stderr = None

        with mock.patch.dict(os.environ, {'foo': 'bar'}, clear=True):
            results = self.run_hook(command=['foo'], env={'hello': 'world'})

            self.assertEqual(results, {'returncode': 0,
                                       'stdout': None,
                                       'stderr': None})
            self.popen_mock.assert_called_once_with(
                ['foo'], stdin=self.devnull, stdout=None, stderr=None,
                env={'hello': 'world', 'foo': 'bar'})
