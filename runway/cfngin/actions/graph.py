"""CFNgin graph action."""
import json
import logging
import sys

from ..plan import merge_graphs
from .base import BaseAction

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

    DESCRIPTION = 'Print graph'

    @property
    def _stack_action(self):
        """Run against a step."""
        return None

    def run(self, **kwargs):
        """Generate the underlying graph and prints it."""
        graph = self._generate_plan(require_unlocked=False,
                                    include_persistent_graph=True).graph
        if self.context.persistent_graph:
            graph = merge_graphs(self.context.persistent_graph, graph)
        if kwargs.get('reduce'):
            # This will performa a transitive reduction on the underlying
            # graph, producing less edges. Mostly useful for the "dot" format,
            # when converting to PNG, so it creates a prettier/cleaner
            # dependency graph.
            graph.transitive_reduction()

        fn = FORMATTERS[kwargs.get('format')]
        fn(sys.stdout, graph)
        sys.stdout.flush()
