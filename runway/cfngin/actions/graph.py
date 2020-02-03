"""CFNgin graph action."""
import json
import logging
import sys

from .base import BaseAction, plan

LOGGER = logging.getLogger(__name__)


def each_step(graph):
    """Yield each step and it's direct dependencies.

    Args:
        graph (:class:`runway.cfngin.plan.Graph`): Graph to iterate over.

    Yields:
        Tuple[Step, Set(str)]

    """
    steps = graph.topological_sort()
    steps.reverse()

    for step in steps:
        deps = graph.downstream(step.name)
        yield step, deps


def dot_format(out, graph, name="digraph"):
    """Output a graph using the graphviz "dot" format.

    Args:
        out (TextIo): Where output will be written.
        graph (:class:`runway.cfngin.plan.Graph`): Graph to be output.
        name (str): Name of the graph.

    """
    out.write("digraph %s {\n" % name)
    for step, deps in each_step(graph):
        for dep in deps:
            out.write("  \"%s\" -> \"%s\";\n" % (step, dep))

    out.write("}\n")


def json_format(out, graph):
    """Output the graph in a machine readable JSON format.

    Args:
        out (TextIo): Where output will be written.
        graph (:class:`runway.cfngin.plan.Graph`): Graph to be output.

    """
    steps = {}
    for step, deps in each_step(graph):
        steps[step.name] = {}
        steps[step.name]["deps"] = [dep.name for dep in deps]

    json.dump({"steps": steps}, out, indent=4)
    out.write("\n")


FORMATTERS = {
    "dot": dot_format,
    "json": json_format,
}


class Action(BaseAction):
    """Responsible for outputing a graph for the current CFNgin config."""

    def _generate_plan(self):
        return plan(
            description="Print graph",
            stack_action=None,
            context=self.context)

    def run(self, **kwargs):
        """Generate the underlying graph and prints it."""
        action_plan = self._generate_plan()
        if kwargs.get('reduce'):
            # This will performa a transitive reduction on the underlying
            # graph, producing less edges. Mostly useful for the "dot" format,
            # when converting to PNG, so it creates a prettier/cleaner
            # dependency graph.
            action_plan.graph.transitive_reduction()

        fn = FORMATTERS[kwargs.get('format')]
        fn(sys.stdout, action_plan.graph)
        sys.stdout.flush()
