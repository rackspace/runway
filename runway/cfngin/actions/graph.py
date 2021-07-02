"""CFNgin graph action."""
from __future__ import annotations

import json
import logging
import sys
from typing import TYPE_CHECKING, Any, Iterable, List, TextIO, Tuple, Union

from ..plan import merge_graphs
from .base import BaseAction

if TYPE_CHECKING:
    from ..plan import Graph, Step

LOGGER = logging.getLogger(__name__)


def each_step(graph: Graph) -> Iterable[Tuple[Step, List[Step]]]:
    """Yield each step and it's direct dependencies.

    Args:
        graph: Graph to iterate over.

    """
    steps = graph.topological_sort()
    steps.reverse()

    for step in steps:
        deps = graph.downstream(step.name)
        yield step, deps


def dot_format(out: TextIO, graph: Graph, name: str = "digraph") -> None:
    """Output a graph using the graphviz "dot" format.

    Args:
        out: Where output will be written.
        graph: Graph to be output.
        name: Name of the graph.

    """
    out.write(f"digraph {name} {{\n")
    for step, deps in each_step(graph):
        for dep in deps:
            out.write(f'  "{step}" -> "{dep}";\n')

    out.write("}\n")


def json_format(out: TextIO, graph: Graph) -> None:
    """Output the graph in a machine readable JSON format.

    Args:
        out: Where output will be written.
        graph: Graph to be output.

    """
    steps = {
        step.name: {"deps": [dep.name for dep in deps]}
        for step, deps in each_step(graph)
    }

    json.dump({"steps": steps}, out, indent=4)
    out.write("\n")


FORMATTERS = {
    "dot": dot_format,
    "json": json_format,
}


class Action(BaseAction):
    """Responsible for outputing a graph for the current CFNgin config."""

    DESCRIPTION = "Print graph"
    NAME = "graph"

    @property
    def _stack_action(self) -> Any:
        """Run against a step."""
        return None

    def run(
        self,
        *,
        concurrency: int = 0,  # pylint: disable=unused-argument
        dump: Union[bool, str] = False,  # pylint: disable=unused-argument
        force: bool = False,  # pylint: disable=unused-argument
        outline: bool = False,  # pylint: disable=unused-argument
        tail: bool = False,  # pylint: disable=unused-argument
        upload_disabled: bool = False,  # pylint: disable=unused-argument
        **kwargs: Any,
    ) -> None:
        """Generate the underlying graph and prints it."""
        graph = self._generate_plan(
            require_unlocked=False, include_persistent_graph=True
        ).graph
        if self.context.persistent_graph:
            graph = merge_graphs(self.context.persistent_graph, graph)
        if kwargs.get("reduce"):
            # This will performa a transitive reduction on the underlying
            # graph, producing less edges. Mostly useful for the "dot" format,
            # when converting to PNG, so it creates a prettier/cleaner
            # dependency graph.
            graph.transitive_reduction()

        fn = FORMATTERS[str(kwargs.get("format", "json"))]
        fn(sys.stdout, graph)
        sys.stdout.flush()
