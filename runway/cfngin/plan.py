"""CFNgin plan, plan componenets, and functions for interacting with a plan."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    NoReturn,
    Optional,
    OrderedDict,
    Set,
    TypeVar,
    Union,
    overload,
)

from .._logging import LogLevels, PrefixAdaptor
from ..utils import merge_dicts
from .dag import DAG, DAGValidationError, walk
from .exceptions import CancelExecution, GraphError, PersistentGraphLocked, PlanFailed
from .stack import Stack
from .status import (
    COMPLETE,
    FAILED,
    PENDING,
    SKIPPED,
    SUBMITTED,
    FailedStatus,
    SkippedStatus,
)
from .ui import ui
from .utils import stack_template_key_name

if TYPE_CHECKING:
    from ..context import CfnginContext
    from .providers.aws.default import Provider
    from .status import Status

LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


@overload
def json_serial(obj: Set[_T]) -> List[_T]:
    ...


@overload
def json_serial(obj: Union[Dict[Any, Any], int, List[Any], str]) -> NoReturn:
    ...


def json_serial(obj: Union[Set[Any], Any]) -> Any:
    """Serialize json.

    Args:
        obj: A python object.

    Example:
        json.dumps(data, default=json_serial)

    """
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def merge_graphs(graph1: Graph, graph2: Graph) -> Graph:
    """Combine two Graphs into one, retaining steps.

    Args:
        graph1: Graph that ``graph2`` will be merged into.
        graph2: Graph that will be merged into ``graph1``.

    """
    merged_graph_dict = merge_dicts(graph1.to_dict().copy(), graph2.to_dict())
    steps = [
        graph1.steps.get(name, graph2.steps.get(name))
        for name in merged_graph_dict.keys()
    ]
    return Graph.from_steps([step for step in steps if step])


class Step:
    """State machine for executing generic actions related to stacks.

    Attributes:
        fn: Function to run to execute the step.
            This function will be ran multiple times until the step is "done".
        last_updated: Time when the step was last updated.
        logger: Logger for logging messages about the step.
        stack: the stack associated with this step
        status: The status of step.
        watch_func: Function that will be called to "tail" the step action.

    """

    fn: Optional[Callable[..., Any]]
    last_updated: float
    logger: PrefixAdaptor
    stack: Stack
    status: Status
    watch_func: Optional[Callable[..., Any]]

    def __init__(
        self,
        stack: Stack,
        *,
        fn: Optional[Callable[..., Any]] = None,
        watch_func: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Instantiate class.

        Args:
            stack: The stack associated
                with this step
            fn: Function to run to execute the step.
                This function will be ran multiple times until the step is "done".
            watch_func: Function that will be called to "tail" the step action.

        """
        self.stack = stack
        self.status = PENDING
        self.last_updated = time.time()
        self.logger = PrefixAdaptor(self.stack.name, LOGGER)
        self.fn = fn
        self.watch_func = watch_func

    def run(self) -> bool:
        """Run this step until it has completed or been skipped."""
        stop_watcher = threading.Event()
        watcher = None
        if self.watch_func:
            watcher = threading.Thread(
                target=self.watch_func, args=(self.stack, stop_watcher)
            )
            watcher.start()

        try:
            while not self.done:
                self._run_once()
        finally:
            if watcher:
                stop_watcher.set()
                watcher.join()
        return self.ok

    def _run_once(self) -> Status:
        """Run a step exactly once."""
        if not self.fn:
            raise TypeError("Step.fn must be type Callable[..., Status] not None")
        try:
            status = self.fn(self.stack, status=self.status)
        except CancelExecution:
            status = SkippedStatus("canceled execution")
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception(err)
            status = FailedStatus(reason=str(err))
        self.set_status(status)
        return status

    @property
    def name(self) -> str:
        """Name of the step.

        This is equal to the name of the stack it operates on.

        """
        return self.stack.name

    @property
    def requires(self) -> Set[str]:
        """Return a list of step names this step depends on."""
        return self.stack.requires

    @property
    def required_by(self) -> Set[str]:
        """Return a list of step names that depend on this step."""
        return self.stack.required_by

    @property
    def completed(self) -> bool:
        """Return True if the step is in a COMPLETE state."""
        return self.status == COMPLETE

    @property
    def skipped(self) -> bool:
        """Return True if the step is in a SKIPPED state."""
        return self.status == SKIPPED

    @property
    def failed(self) -> bool:
        """Return True if the step is in a FAILED state."""
        return self.status == FAILED

    @property
    def done(self) -> bool:
        """Return True if the step is finished.

        To be ``True``, status must be either COMPLETE, SKIPPED or FAILED)

        """
        return self.completed or self.skipped or self.failed

    @property
    def ok(self) -> bool:
        """Return True if the step is finished (either COMPLETE or SKIPPED)."""
        return self.completed or self.skipped

    @property
    def submitted(self) -> bool:
        """Return True if the step is SUBMITTED, COMPLETE, or SKIPPED."""
        return self.status >= SUBMITTED

    def set_status(self, status: Status) -> None:
        """Set the current step's status.

        Args:
            status: The status to set the step to.

        """
        if status is not self.status:
            LOGGER.debug("setting %s state to %s...", self.stack.name, status.name)
            self.status = status
            self.last_updated = time.time()
            if self.stack.logging:
                self.log_step()

    def complete(self) -> None:
        """Shortcut for ``set_status(COMPLETE)``."""
        self.set_status(COMPLETE)

    def log_step(self) -> None:
        """Construct a log message for a set and log it to the UI."""
        msg = self.status.name
        if self.status.reason:
            msg += f" ({self.status.reason})"
        if self.status.code == SUBMITTED.code:
            ui.log(LogLevels.NOTICE, msg, logger=self.logger)
        elif self.status.code == COMPLETE.code:
            ui.log(LogLevels.SUCCESS, msg, logger=self.logger)
        elif self.status.code == FAILED.code:
            ui.log(LogLevels.ERROR, msg, logger=self.logger)
        else:
            ui.info(msg, logger=self.logger)

    def skip(self) -> None:
        """Shortcut for ``set_status(SKIPPED)``."""
        self.set_status(SKIPPED)

    def submit(self) -> None:
        """Shortcut for ``set_status(SUBMITTED)``."""
        self.set_status(SUBMITTED)

    @classmethod
    def from_stack_name(
        cls,
        stack_name: str,
        context: CfnginContext,
        requires: Optional[Union[List[str], Set[str]]] = None,
        fn: Optional[Callable[..., Status]] = None,
        watch_func: Optional[Callable[..., Any]] = None,
    ) -> Step:
        """Create a step using only a stack name.

        Args:
            stack_name: Name of a CloudFormation stack.
            context: Context object. Required to initialize a "fake"
                :class:`runway.cfngin.stack.Stack`.
            requires: Stacks that this stack depends on.
            fn: The function to run to execute the step.
                This function will be ran multiple times until the step is "done".
            watch_func: an optional function that will be called to "tail" the
                step action.

        """
        # pylint: disable=import-outside-toplevel
        from runway.config.models.cfngin import CfnginStackDefinitionModel

        stack_def = CfnginStackDefinitionModel.construct(
            name=stack_name, requires=requires or []
        )
        stack = Stack(stack_def, context)
        return cls(stack, fn=fn, watch_func=watch_func)

    @classmethod
    def from_persistent_graph(
        cls,
        graph_dict: Union[
            Dict[str, List[str]], Dict[str, Set[str]], OrderedDict[str, Set[str]]
        ],
        context: CfnginContext,
        fn: Optional[Callable[..., Status]] = None,
        watch_func: Optional[Callable[..., Any]] = None,
    ) -> List[Step]:
        """Create a steps for a persistent graph dict.

        Args:
            graph_dict: A graph dict.
            context: Context object. Required to initialize a "fake"
                :class:`runway.cfngin.stack.Stack`.
            requires: Stacks that this stack depends on.
            fn: The function to run to execute the step.
                This function will be ran multiple times until the step is "done".
            watch_func: an optional function that will be called to "tail" the
                step action.

        """
        return [
            cls.from_stack_name(name, context, requires, fn, watch_func)
            for name, requires in graph_dict.items()
        ]

    def __repr__(self) -> str:
        """Object represented as a string."""
        return f"<CFNgin.plan.Step:{self.stack.name}>"

    def __str__(self) -> str:
        """Object displayed as a string."""
        return self.stack.name


class Graph:
    """Graph represents a graph of steps.

    The :class:`Graph` helps organize the steps needed to execute a particular
    action for a set of :class:`runway.cfngin.stack.Stack` objects. When
    initialized with a set of steps, it will first build a Directed Acyclic
    Graph from the steps and their dependencies.

    Example:
        >>> dag = DAG()
        >>> a = Step("a", fn=deploy)
        >>> b = Step("b", fn=deploy)
        >>> dag.add_step(a)
        >>> dag.add_step(b)
        >>> dag.connect(a, b)

    """

    dag: DAG
    steps: Dict[str, Step]

    def __init__(
        self, steps: Optional[Dict[str, Step]] = None, dag: Optional[DAG] = None
    ) -> None:
        """Instantiate class.

        Args:
            steps: Dict with key of step name and value of :class:`Step` for
                steps to initialize the Graph with. Note that if this is provided,
                a pre-configured :class:`runway.cfngin.dag.DAG` that already
                includes these steps should also be provided..
            dag: An optional :class:`runway.cfngin.dag.DAG` object. If one is
                not provided, a new one will be initialized.

        """
        self.steps = steps or {}
        self.dag = dag or DAG()

    def add_step(
        self, step: Step, add_dependencies: bool = False, add_dependants: bool = False
    ) -> None:
        """Add a step to the graph.

        Args:
            step: The step to be added.
            add_dependencies: Connect steps that need to be completed before this
                step.
            add_dependants: Connect steps that require this step.

        """
        self.steps[step.name] = step
        self.dag.add_node(step.name)

        if add_dependencies:
            for dep in step.requires:
                self.connect(step.name, dep)

        if add_dependants:
            for parent in step.required_by:
                self.connect(parent, step.name)

    def add_step_if_not_exists(
        self, step: Step, add_dependencies: bool = False, add_dependants: bool = False
    ) -> None:
        """Try to add a step to the graph.

        Can be used when failure to add is acceptable.

        Args:
            step: The step to be added.
            add_dependencies: Connect steps that need to be completed before this
                step.
            add_dependants: Connect steps that require this step.

        """
        if self.steps.get(step.name):
            return

        self.steps[step.name] = step
        self.dag.add_node_if_not_exists(step.name)

        if add_dependencies:
            for dep in step.requires:
                try:
                    self.connect(step.name, dep)
                except GraphError:
                    continue

        if add_dependants:
            for parent in step.required_by:
                try:
                    self.connect(parent, step.name)
                except GraphError:
                    continue

    def add_steps(self, steps: List[Step]) -> None:
        """Add a list of steps.

        Args:
            steps: The step to be added.

        """
        for step in steps:
            self.add_step(step)

        for step in steps:
            for dep in step.requires:
                self.connect(step.name, dep)

            for parent in step.required_by:
                self.connect(parent, step.name)

    def pop(self, step: Step, default: Any = None) -> Any:
        """Remove a step from the graph.

        Args:
            step: The step to remove from the graph.
            default: Returned if the step could not be popped

        """
        self.dag.delete_node_if_exists(step.name)
        return self.steps.pop(step.name, default)

    def connect(self, step: str, dep: str) -> None:
        """Connect a dependency to a step.

        Args:
            step: Step name to add a dependency to.
            dep: Name of dependent step.

        """
        try:
            self.dag.add_edge(step, dep)
        except (DAGValidationError, KeyError) as exc:
            raise GraphError(exc, step, dep) from None

    def transitive_reduction(self) -> None:
        """Perform a transitive reduction on the underlying DAG.

        The transitive reduction of a graph is a graph with as few edges as
        possible with the same reachability as the original graph.

        See https://en.wikipedia.org/wiki/Transitive_reduction

        """
        self.dag.transitive_reduction()

    def walk(
        self,
        walker: Callable[[DAG, Callable[[str], Any]], Any],
        walk_func: Callable[[Step], Any],
    ) -> Any:
        """Walk the steps of the graph.

        Args:
            walker: Function used to walk the steps.
            walk_func: Function called with a :class:`Step` as the only argument
                for each step of the plan.

        """

        def fn(step_name: str) -> Any:
            """Get a step by step name and execute the ``walk_func`` on it.

            Args:
                step_name: Name of a step.

            """
            step = self.steps[step_name]
            return walk_func(step)

        return walker(self.dag, fn)

    def downstream(self, step_name: str) -> List[Step]:
        """Return the direct dependencies of the given step."""
        return [self.steps[dep] for dep in self.dag.downstream(step_name)]

    def transposed(self) -> Graph:
        """Return a "transposed" version of this graph.

        Useful for walking in reverse.

        """
        return Graph(steps=self.steps, dag=self.dag.transpose())

    def filtered(self, step_names: List[str]) -> Graph:
        """Return a "filtered" version of this graph.

        Args:
            step_names: Steps to filter.

        """
        return Graph(steps=self.steps, dag=self.dag.filter(step_names))

    def topological_sort(self) -> List[Step]:
        """Perform a topological sort of the underlying DAG."""
        nodes = self.dag.topological_sort()
        return [self.steps[step_name] for step_name in nodes]

    def to_dict(self) -> OrderedDict[str, Set[str]]:
        """Return the underlying DAG as a dictionary."""
        return self.dag.graph

    def dumps(self, indent: Optional[int] = None) -> str:
        """Output the graph as a json seralized string for storage.

        Args:
            indent: Number of spaces for each indentation.

        """
        return json.dumps(self.to_dict(), default=json_serial, indent=indent)

    @classmethod
    def from_dict(
        cls,
        graph_dict: Union[
            Dict[str, List[str]], Dict[str, Set[str]], OrderedDict[str, Set[str]]
        ],
        context: CfnginContext,
    ) -> Graph:
        """Create a Graph from a graph dict.

        Args:
            graph_dict: The dictionary used to create the graph.
            context: Required to init stacks.

        """
        return cls.from_steps(Step.from_persistent_graph(graph_dict, context))

    @classmethod
    def from_steps(cls, steps: List[Step]) -> Graph:
        """Create a Graph from Steps.

        Args:
            steps: Steps used to create the graph.

        """
        graph = cls()
        graph.add_steps(steps)
        return graph

    def __str__(self) -> str:
        """Object displayed as a string."""
        return self.dumps()


class Plan:
    """A convenience class for working on a Graph.

    Attributes:
        context: Context object.
        description: Plan description.
        graph: Graph of the plan.
        id: UUID for the plan.
        reverse: The graph has been transposed for walking in reverse.
        require_unlocked: Require the persistent graph to be unlocked before
            executing steps.

    """

    context: Optional[CfnginContext]
    description: str
    graph: Graph
    id: uuid.UUID
    require_unlocked: bool
    reverse: bool

    def __init__(
        self,
        description: str,
        graph: Graph,
        context: Optional[CfnginContext] = None,
        reverse: bool = False,
        require_unlocked: bool = True,
    ) -> None:
        """Initialize class.

        Args:
            description: Description of what the plan is going to do.
            graph: Local graph used for the plan.
            context: Context object.
            reverse: Transpose the graph for walking in reverse.
            require_unlocked: Require the persistent graph to be
                unlocked before executing steps.

        """
        self.context = context
        self.description = description
        self.id = uuid.uuid4()
        self.reverse = reverse
        self.require_unlocked = require_unlocked

        if self.reverse:
            graph = graph.transposed()

        if self.context:
            self.locked = self.context.persistent_graph_locked

            if self.context.stack_names:
                nodes = [
                    target
                    for target in self.context.stack_names
                    if graph.steps.get(target)
                ]

                graph = graph.filtered(nodes)
        else:
            self.locked = False

        self.graph = graph

    def outline(self, level: int = logging.INFO, message: str = ""):
        """Print an outline of the actions the plan is going to take.

        The outline will represent the rough ordering of the steps that will be
        taken.

        Args:
            level: a valid log level that should be used to log
                the outline
            message: a message that will be logged to
                the user after the outline has been logged.

        """
        LOGGER.log(level, 'plan "%s":', self.description)
        for steps, step in enumerate(self.steps, start=1):
            LOGGER.log(
                level,
                '  - step: %s: target: "%s", action: "%s"',
                steps,
                step.name,
                step.fn.__name__ if callable(step.fn) else step.fn,
            )
        if message:
            LOGGER.log(level, message)

    def dump(
        self,
        *,
        directory: str,
        context: CfnginContext,
        provider: Optional[Provider] = None,
    ) -> Any:
        """Output the rendered blueprint for all stacks in the plan.

        Args:
            directory: Directory where files will be created.
            context: Current CFNgin context.
            provider: Provider to use when resolving the blueprints.

        """
        LOGGER.info('dumping "%s"...', self.description)
        directory = os.path.expanduser(directory)
        if not os.path.exists(directory):
            os.makedirs(directory)

        def walk_func(step: Step) -> bool:
            """Walk function."""
            step.stack.resolve(context=context, provider=provider)
            blueprint = step.stack.blueprint
            filename = stack_template_key_name(blueprint)
            path = os.path.join(directory, filename)

            blueprint_dir = os.path.dirname(path)
            if not os.path.exists(blueprint_dir):
                os.makedirs(blueprint_dir)

            LOGGER.info('writing stack "%s" -> %s', step.name, path)
            with open(path, "w", encoding="utf-8") as _file:
                _file.write(blueprint.rendered)

            return True

        return self.graph.walk(walk, walk_func)

    def execute(self, *args: Any, **kwargs: Any):
        """Walk each step in the underlying graph.

        Raises:
            PersistentGraphLocked: Raised if the persistent graph is
                locked prior to execution and this session did not lock it.
            PlanFailed: Raised if any of the steps fail.

        """
        if self.locked and self.require_unlocked:
            raise PersistentGraphLocked
        self.walk(*args, **kwargs)

        failed_steps = [step for step in self.steps if step.status == FAILED]
        if failed_steps:
            raise PlanFailed(failed_steps)

    def walk(self, walker: Callable[..., Any]) -> Any:
        """Walk each step in the underlying graph, in topological order.

        Args:
            walker: a walker function to be passed to :class:`runway.cfngin.dag.DAG`
                to walk the graph.

        """

        def walk_func(step: Step) -> bool:
            """Execute a :class:`Step` wile walking the graph.

            Handles updating the persistent graph if one is being used.

            Args:
                step: :class:`Step` to execute.

            """
            # Before we execute the step, we need to ensure that it's
            # transitive dependencies are all in an "ok" state. If not, we
            # won't execute this step.
            for dep in self.graph.downstream(step.name):
                if not dep.ok:
                    step.set_status(FailedStatus("dependency has failed"))
                    return step.ok

            result = step.run()

            if not self.context or not self.context.persistent_graph:
                return result

            if step.completed or (
                step.skipped
                and step.status.reason == ("does not exist in cloudformation")
            ):
                fn_name = step.fn.__name__ if callable(step.fn) else step.fn
                if fn_name == "_destroy_stack":
                    self.context.persistent_graph.pop(step)
                    LOGGER.debug(
                        "removed step '%s' from the persistent graph", step.name
                    )
                elif fn_name == "_launch_stack":
                    self.context.persistent_graph.add_step_if_not_exists(
                        step, add_dependencies=True, add_dependants=True
                    )
                    LOGGER.debug("added step '%s' to the persistent graph", step.name)
                else:
                    return result
                self.context.put_persistent_graph(self.lock_code)
            return result

        return self.graph.walk(walker, walk_func)

    @property
    def lock_code(self) -> str:
        """Code to lock/unlock the persistent graph."""
        return str(self.id)

    @property
    def steps(self) -> List[Step]:
        """Return a list of all steps in the plan."""
        steps = self.graph.topological_sort()
        steps.reverse()
        return steps

    @property
    def step_names(self) -> List[str]:
        """Return a list of all step names."""
        return [step.name for step in self.steps]

    def keys(self) -> List[str]:
        """Return a list of all step names."""
        return self.step_names
