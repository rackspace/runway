"""Tests for runway.cfngin.plan."""

# pyright: basic
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import mock

from runway.cfngin.dag import walk
from runway.cfngin.exceptions import (
    CancelExecution,
    GraphError,
    PersistentGraphLocked,
    PlanFailed,
)
from runway.cfngin.lookups.registry import (
    register_lookup_handler,
    unregister_lookup_handler,
)
from runway.cfngin.plan import Graph, Plan, Step
from runway.cfngin.stack import Stack
from runway.cfngin.status import COMPLETE, FAILED, SKIPPED, SUBMITTED
from runway.cfngin.utils import stack_template_key_name
from runway.config import CfnginConfig
from runway.context import CfnginContext
from runway.lookups.handlers.base import LookupHandler

from .factories import generate_definition, mock_context

if TYPE_CHECKING:
    from runway.cfngin.status import Status


class TestStep(unittest.TestCase):
    """Tests for runway.cfngin.plan.Step."""

    def setUp(self) -> None:
        """Run before tests."""
        stack = mock.MagicMock()
        stack.name = "stack"
        stack.fqn = "namespace-stack"
        self.step = Step(stack=stack, fn=None)

    def test_status(self) -> None:
        """Test status."""
        self.assertFalse(self.step.submitted)
        self.assertFalse(self.step.completed)

        self.step.submit()
        self.assertEqual(self.step.status, SUBMITTED)
        self.assertTrue(self.step.submitted)
        self.assertFalse(self.step.completed)

        self.step.complete()
        self.assertEqual(self.step.status, COMPLETE)
        self.assertNotEqual(self.step.status, SUBMITTED)
        self.assertTrue(self.step.submitted)
        self.assertTrue(self.step.completed)

        self.assertNotEqual(self.step.status, True)
        self.assertNotEqual(self.step.status, False)
        self.assertNotEqual(self.step.status, "banana")

    def test_from_stack_name(self) -> None:
        """Return step from step name."""
        context = mock_context()
        stack_name = "test-stack"
        result = Step.from_stack_name(stack_name, context)

        self.assertIsInstance(result, Step)
        self.assertEqual(stack_name, result.stack.name)

    def test_from_persistent_graph(self) -> None:
        """Return list of steps from graph dict."""
        context = mock_context()
        graph_dict: Dict[str, Any] = {"stack1": [], "stack2": ["stack1"]}
        result = Step.from_persistent_graph(graph_dict, context)

        self.assertEqual(2, len(result))
        self.assertIsInstance(result, list)

        for step in result:
            self.assertIsInstance(step, Step)
            self.assertIn(step.stack.name, graph_dict.keys())


class TestGraph(unittest.TestCase):
    """Tests for runway.cfngin.plan.Graph."""

    def setUp(self) -> None:
        """Run before tests."""
        self.context = mock_context()
        self.graph_dict: Dict[str, Any] = {"stack1": [], "stack2": ["stack1"]}
        self.graph_dict_expected = {"stack1": set(), "stack2": {"stack1"}}
        self.steps = Step.from_persistent_graph(self.graph_dict, self.context)

    def test_add_steps(self) -> None:
        """Test add steps."""
        graph = Graph()
        graph.add_steps(self.steps)

        self.assertEqual(self.steps, list(graph.steps.values()))
        self.assertEqual([step.name for step in self.steps], list(graph.steps.keys()))
        self.assertEqual(self.graph_dict_expected, graph.to_dict())

    def test_pop(self) -> None:
        """Test pop."""
        graph = Graph()
        graph.add_steps(self.steps)

        stack2 = next(step for step in self.steps if step.name == "stack2")

        self.assertEqual(stack2, graph.pop(stack2))
        self.assertEqual({"stack1": set()}, graph.to_dict())

    def test_dumps(self) -> None:
        """Test dumps."""
        graph = Graph()
        graph.add_steps(self.steps)

        self.assertEqual(json.dumps(self.graph_dict), graph.dumps())

    def test_from_dict(self) -> None:
        """Test from dict."""
        graph = Graph.from_dict(self.graph_dict, self.context)

        self.assertIsInstance(graph, Graph)
        self.assertEqual([step.name for step in self.steps], list(graph.steps.keys()))
        self.assertEqual(self.graph_dict_expected, graph.to_dict())

    def test_from_steps(self) -> None:
        """Test from steps."""
        graph = Graph.from_steps(self.steps)

        self.assertEqual(self.steps, list(graph.steps.values()))
        self.assertEqual([step.name for step in self.steps], list(graph.steps.keys()))
        self.assertEqual(self.graph_dict_expected, graph.to_dict())


class TestPlan(unittest.TestCase):
    """Tests for runway.cfngin.plan.Plan."""

    def setUp(self) -> None:
        """Run before tests."""
        self.count = 0
        self.config = CfnginConfig.parse_obj({"namespace": "namespace"})
        self.context = CfnginContext(config=self.config)

        class FakeLookup(LookupHandler):
            """False Lookup."""

            @classmethod
            def handle(cls, value: str, *__args: Any, **__kwargs: Any) -> str:  # type: ignore
                """Perform the lookup."""
                return "test"

        register_lookup_handler("noop", FakeLookup)

    def tearDown(self) -> None:
        """Run after tests."""
        unregister_lookup_handler("noop")

    def test_plan(self) -> None:
        """Test plan."""
        vpc = Stack(definition=generate_definition("vpc", 1), context=self.context)
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=[vpc.name]),
            context=self.context,
        )

        graph = Graph.from_steps([Step(vpc, fn=None), Step(bastion, fn=None)])
        plan = Plan(description="Test", graph=graph)

        self.assertEqual(plan.graph.to_dict(), {"bastion-1": {"vpc-1"}, "vpc-1": set()})

    def test_plan_reverse(self) -> None:
        """Test plan reverse."""
        vpc = Stack(definition=generate_definition("vpc", 1), context=self.context)
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=[vpc.name]),
            context=self.context,
        )
        graph = Graph.from_steps([Step(vpc, fn=None), Step(bastion, fn=None)])
        plan = Plan(description="Test", graph=graph, reverse=True)

        # order is different between python2/3 so can't compare dicts
        result_graph_dict = plan.graph.to_dict()
        self.assertEqual(set(), result_graph_dict.get("bastion-1"))
        self.assertEqual({"bastion-1"}, result_graph_dict.get("vpc-1"))

    def test_plan_targeted(self) -> None:
        """Test plan targeted."""
        context = CfnginContext(config=self.config)
        vpc = Stack(definition=generate_definition("vpc", 1), context=context)
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=[vpc.name]),
            context=context,
        )
        context.stack_names = [vpc.name]
        graph = Graph.from_steps([Step(vpc, fn=None), Step(bastion, fn=None)])
        plan = Plan(description="Test", graph=graph, context=context)

        self.assertEqual({vpc.name: set()}, plan.graph.to_dict())

    def test_execute_plan(self) -> None:
        """Test execute plan."""
        context = CfnginContext(config=self.config)
        context.put_persistent_graph = mock.MagicMock()
        vpc = Stack(definition=generate_definition("vpc", 1), context=context)
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=[vpc.name]),
            context=context,
        )
        removed = Stack(
            definition=generate_definition("removed", 1, requires=[]), context=context
        )
        context._persistent_graph = Graph.from_steps([Step(removed)])

        calls: List[str] = []

        def _launch_stack(stack: Stack, status: Optional[Status] = None) -> Status:
            calls.append(stack.fqn)
            return COMPLETE

        def _destroy_stack(stack: Stack, status: Optional[Status] = None) -> Status:
            calls.append(stack.fqn)
            return COMPLETE

        graph = Graph.from_steps(
            [
                Step(removed, fn=_destroy_stack),
                Step(vpc, fn=_launch_stack),
                Step(bastion, fn=_launch_stack),
            ]
        )
        plan = Plan(description="Test", graph=graph, context=context)
        plan.context._persistent_graph_lock_code = plan.lock_code  # type: ignore
        plan.execute(walk)

        # the order these are appended changes between python2/3
        self.assertIn("namespace-vpc-1", calls)
        self.assertIn("namespace-bastion-1", calls)
        self.assertIn("namespace-removed-1", calls)
        context.put_persistent_graph.assert_called()

        # order is different between python2/3 so can't compare dicts
        result_graph_dict = context.persistent_graph.to_dict()  # type: ignore
        self.assertEqual(2, len(result_graph_dict))
        self.assertEqual(set(), result_graph_dict.get("vpc-1"))
        self.assertEqual({"vpc-1"}, result_graph_dict.get("bastion-1"))
        self.assertIsNone(result_graph_dict.get("namespace-removed-1"))

    def test_execute_plan_no_persist(self) -> None:
        """Test execute plan with no persistent graph."""
        context = CfnginContext(config=self.config)
        context.put_persistent_graph = mock.MagicMock()
        vpc = Stack(definition=generate_definition("vpc", 1), context=context)
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=[vpc.name]),
            context=context,
        )

        calls: List[str] = []

        def _launch_stack(stack: Stack, status: Optional[Status] = None) -> Status:
            calls.append(stack.fqn)
            return COMPLETE

        graph = Graph.from_steps(
            [Step(vpc, fn=_launch_stack), Step(bastion, fn=_launch_stack)]
        )
        plan = Plan(description="Test", graph=graph, context=context)

        plan.execute(walk)

        self.assertEqual(calls, ["namespace-vpc-1", "namespace-bastion-1"])
        context.put_persistent_graph.assert_not_called()

    def test_execute_plan_locked(self) -> None:
        """Test execute plan locked.

        Locked stacks still need to have their requires evaluated when
        they're being created.

        """
        vpc = Stack(definition=generate_definition("vpc", 1), context=self.context)
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=[vpc.name]),
            locked=True,
            context=self.context,
        )

        calls: List[str] = []

        def fn(stack: Stack, status: Optional[Status] = None) -> Status:
            calls.append(stack.fqn)
            return COMPLETE

        graph = Graph.from_steps([Step(vpc, fn=fn), Step(bastion, fn=fn)])
        plan = Plan(description="Test", graph=graph)
        plan.execute(walk)

        self.assertEqual(calls, ["namespace-vpc-1", "namespace-bastion-1"])

    def test_execute_plan_filtered(self) -> None:
        """Test execute plan filtered."""
        vpc = Stack(definition=generate_definition("vpc", 1), context=self.context)
        db = Stack(
            definition=generate_definition("db", 1, requires=[vpc.name]),
            context=self.context,
        )
        app = Stack(
            definition=generate_definition("app", 1, requires=[db.name]),
            context=self.context,
        )

        calls: List[str] = []

        def fn(stack: Stack, status: Optional[Status] = None) -> Status:
            calls.append(stack.fqn)
            return COMPLETE

        context = mock.MagicMock()
        context.persistent_graph_locked = False
        context.stack_names = ["db-1"]
        graph = Graph.from_steps([Step(vpc, fn=fn), Step(db, fn=fn), Step(app, fn=fn)])
        plan = Plan(context=context, description="Test", graph=graph)
        plan.execute(walk)

        self.assertEqual(calls, ["namespace-vpc-1", "namespace-db-1"])

    def test_execute_plan_exception(self) -> None:
        """Test execute plan exception."""
        vpc = Stack(definition=generate_definition("vpc", 1), context=self.context)
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=[vpc.name]),
            context=self.context,
        )

        calls: List[str] = []

        def fn(stack: Stack, status: Optional[Status] = None) -> Status:
            calls.append(stack.fqn)
            if stack.name == vpc_step.name:
                raise ValueError("Boom")
            return COMPLETE

        vpc_step = Step(vpc, fn=fn)
        bastion_step = Step(bastion, fn=fn)

        graph = Graph.from_steps([vpc_step, bastion_step])
        plan = Plan(description="Test", graph=graph)

        with self.assertRaises(PlanFailed):
            plan.execute(walk)

        self.assertEqual(calls, ["namespace-vpc-1"])
        self.assertEqual(vpc_step.status, FAILED)

    def test_execute_plan_skipped(self) -> None:
        """Test execute plan skipped."""
        vpc = Stack(definition=generate_definition("vpc", 1), context=self.context)
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=[vpc.name]),
            context=self.context,
        )

        calls: List[str] = []

        def fn(stack: Stack, status: Optional[Status] = None) -> Status:
            calls.append(stack.fqn)
            if stack.fqn == vpc_step.name:
                return SKIPPED
            return COMPLETE

        vpc_step = Step(vpc, fn=fn)
        bastion_step = Step(bastion, fn=fn)

        graph = Graph.from_steps([vpc_step, bastion_step])
        plan = Plan(description="Test", graph=graph)
        plan.execute(walk)

        self.assertEqual(calls, ["namespace-vpc-1", "namespace-bastion-1"])

    def test_execute_plan_failed(self) -> None:
        """Test execute plan failed."""
        vpc = Stack(definition=generate_definition("vpc", 1), context=self.context)
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=[vpc.name]),
            context=self.context,
        )
        db = Stack(definition=generate_definition("db", 1), context=self.context)

        calls: List[str] = []

        def fn(stack: Stack, status: Optional[Status] = None) -> Status:
            calls.append(stack.fqn)
            if stack.name == vpc_step.name:
                return FAILED
            return COMPLETE

        vpc_step = Step(vpc, fn=fn)
        bastion_step = Step(bastion, fn=fn)
        db_step = Step(db, fn=fn)

        graph = Graph.from_steps([vpc_step, bastion_step, db_step])
        plan = Plan(description="Test", graph=graph)
        with self.assertRaises(PlanFailed):
            plan.execute(walk)

        calls.sort()

        self.assertEqual(calls, ["namespace-db-1", "namespace-vpc-1"])

    def test_execute_plan_cancelled(self) -> None:
        """Test execute plan cancelled."""
        vpc = Stack(definition=generate_definition("vpc", 1), context=self.context)
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=[vpc.name]),
            context=self.context,
        )

        calls: List[str] = []

        def fn(stack: Stack, status: Optional[Status] = None) -> Status:
            calls.append(stack.fqn)
            if stack.fqn == vpc_step.name:
                raise CancelExecution
            return COMPLETE

        vpc_step = Step(vpc, fn=fn)
        bastion_step = Step(bastion, fn=fn)

        graph = Graph.from_steps([vpc_step, bastion_step])
        plan = Plan(description="Test", graph=graph)
        plan.execute(walk)

        self.assertEqual(calls, ["namespace-vpc-1", "namespace-bastion-1"])

    def test_execute_plan_graph_locked(self) -> None:
        """Test execute plan with locked persistent graph."""
        context = CfnginContext(config=self.config)
        context._persistent_graph = Graph.from_dict({"stack1": []}, context)
        context._persistent_graph_lock_code = "1111"
        plan = Plan(description="Test", graph=Graph(), context=context)
        with self.assertRaises(PersistentGraphLocked):
            plan.execute()

    def test_build_graph_missing_dependency(self) -> None:
        """Test build graph missing dependency."""
        bastion = Stack(
            definition=generate_definition("bastion", 1, requires=["vpc-1"]),
            context=self.context,
        )

        with self.assertRaises(GraphError) as expected:
            Graph.from_steps([Step(bastion)])
        message_starts = (
            "Error detected when adding 'vpc-1' as a dependency of 'bastion-1':"
        )
        message_contains = "dependent node vpc-1 does not exist"
        self.assertTrue(str(expected.exception).startswith(message_starts))
        self.assertTrue(message_contains in str(expected.exception))

    def test_build_graph_cyclic_dependencies(self) -> None:
        """Test build graph cyclic dependencies."""
        vpc = Stack(definition=generate_definition("vpc", 1), context=self.context)
        db = Stack(
            definition=generate_definition("db", 1, requires=["app-1"]),
            context=self.context,
        )
        app = Stack(
            definition=generate_definition("app", 1, requires=["db-1"]),
            context=self.context,
        )

        with self.assertRaises(GraphError) as expected:
            Graph.from_steps([Step(vpc), Step(db), Step(app)])
        message = (
            "Error detected when adding 'db-1' "
            "as a dependency of 'app-1': graph is "
            "not acyclic"
        )
        self.assertEqual(str(expected.exception), message)

    def test_dump(self) -> None:
        """Test dump."""
        requires: List[str] = []
        steps: List[Step] = []

        for i in range(5):
            overrides = {
                "variables": {
                    "PublicSubnets": "1",
                    "SshKeyName": "1",
                    "PrivateSubnets": "1",
                    "Random": "${noop something}",
                },
                "requires": requires,
            }

            stack = Stack(
                definition=generate_definition("vpc", i, **overrides),
                context=self.context,
            )
            requires = [stack.name]

            steps += [Step(stack)]

        graph = Graph.from_steps(steps)
        plan = Plan(description="Test", graph=graph)

        tmp_dir = tempfile.mkdtemp()
        try:
            plan.dump(directory=tmp_dir, context=self.context)

            for step in plan.steps:
                template_path = os.path.join(
                    tmp_dir, stack_template_key_name(step.stack.blueprint)  # type: ignore
                )
                self.assertTrue(os.path.isfile(template_path))
        finally:
            shutil.rmtree(tmp_dir)
