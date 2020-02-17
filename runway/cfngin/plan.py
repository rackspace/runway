"""CFNgin plan, plan componenets, and functions for interacting with a plan."""
import json
import logging
import os
import threading
import time
import uuid

from .dag import DAG, DAGValidationError, walk
from .exceptions import (CancelExecution, GraphError, PersistentGraphLocked,
                         PlanFailed)
from .status import (COMPLETE, FAILED, PENDING, SKIPPED, SUBMITTED,
                     FailedStatus, SkippedStatus)
from .ui import ui
from .util import merge_map, stack_template_key_name

LOGGER = logging.getLogger(__name__)

COLOR_CODES = {
    SUBMITTED.code: 33,  # yellow
    COMPLETE.code: 32,   # green
    FAILED.code: 31,     # red
}


def json_serial(obj):
    """Serialize json.

    Args:
        obj (Any): A python object.

    Example:
        json.dumps(data, default=json_serial)

    """
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def log_step(step):
    """Construct a log message for a set and log it to the UI.

    Args:
        step (:class:`Step`): The step to be logged.

    """
    msg = "%s: %s" % (step, step.status.name)
    if step.status.reason:
        msg += " (%s)" % (step.status.reason)
    color_code = COLOR_CODES.get(step.status.code, 37)
    ui.info(msg, extra={"color": color_code})


def merge_graphs(graph1, graph2):
    """Combine two Graphs into one, retaining steps.

    Args:
        graph1 (:class:`Graph`): Graph that ``graph2`` will
            be merged into.
        graph2 (:class:`Graph`): Graph that will be merged
            into ``graph1``.

    Returns:
        :class:`Graph`: A combined graph.

    """
    merged_graph_dict = merge_map(graph1.to_dict().copy(),
                                  graph2.to_dict())
    steps = [graph1.steps.get(name, graph2.steps.get(name))
             for name in merged_graph_dict.keys()]
    return Graph.from_steps(steps)


class Step(object):
    """State machine for executing generic actions related to stacks.

    Attributes:
        fn (Optional[Callable]): Function to run to execute the step.
            This function will be ran multiple times until the step is "done".
        last_updated (float): Time when the step was last updated.
        stack (:class:`runway.cfngin.stack.Stack`): the stack associated with
            this step
        status (:class:`runway.cfngin.status.Status`): The status of step.
        watch_func (Optional[Callable]): Function that will be called to
            "tail" the step action.

    """

    def __init__(self, stack, fn=None, watch_func=None):
        """Instantiate class.

        Args:
            stack (:class:`runway.cfngin.stack.Stack`): The stack associated
                with this step
            fn (Optional[Callable]): Function to run to execute the step.
                This function will be ran multiple times until the step is
                "done".
            watch_func (Optional[Callable]): Function that will be called to
                "tail" the step action.

        """
        self.stack = stack
        self.status = PENDING
        self.last_updated = time.time()
        self.fn = fn
        self.watch_func = watch_func

    def run(self):
        """Run this step until it has completed or been skipped.

        Returns:
            bool

        """
        stop_watcher = threading.Event()
        watcher = None
        if self.watch_func:
            watcher = threading.Thread(
                target=self.watch_func,
                args=(self.stack, stop_watcher)
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

    def _run_once(self):
        """Run a step exactly once.

        Returns:
            str

        """
        try:
            status = self.fn(self.stack, status=self.status)
        except CancelExecution:
            status = SkippedStatus('canceled execution')
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception(err)
            status = FailedStatus(reason=str(err))
        self.set_status(status)
        return status

    @property
    def name(self):
        """Name of the step.

        This is equal to the name of the stack it operates on.

        Returns:
            str

        """
        return self.stack.name

    @property
    def requires(self):
        """Return a list of step names this step depends on.

        Returns:
            List[str]

        """
        return self.stack.requires

    @property
    def required_by(self):
        """Return a list of step names that depend on this step.

        Returns:
            List[str]

        """
        return self.stack.required_by

    @property
    def completed(self):
        """Return True if the step is in a COMPLETE state.

        Returns:
            bool

        """
        return self.status == COMPLETE

    @property
    def skipped(self):
        """Return True if the step is in a SKIPPED state.

        Returns:
            bool

        """
        return self.status == SKIPPED

    @property
    def failed(self):
        """Return True if the step is in a FAILED state.

        Returns:
            bool

        """
        return self.status == FAILED

    @property
    def done(self):
        """Return True if the step is finished.

        To be ``True``, status must be either COMPLETE, SKIPPED or FAILED)

        Returns:
            bool

        """
        return self.completed or self.skipped or self.failed

    @property
    def ok(self):
        """Return True if the step is finished (either COMPLETE or SKIPPED).

        Returns:
            bool

        """
        return self.completed or self.skipped

    @property
    def submitted(self):
        """Return True if the step is SUBMITTED, COMPLETE, or SKIPPED.

        Returns:
            bool

        """
        return self.status >= SUBMITTED

    def set_status(self, status):
        """Set the current step's status.

        Args:
            status (:class:`runway.cfngin.status.Status`): The status to set the
                step to.

        """
        if status is not self.status:
            LOGGER.debug("Setting %s state to %s.", self.stack.name,
                         status.name)
            self.status = status
            self.last_updated = time.time()
            if self.stack.logging:
                log_step(self)

    def complete(self):
        """Shortcut for ``set_status(COMPLETE)``."""
        self.set_status(COMPLETE)

    def skip(self):
        """Shortcut for ``set_status(SKIPPED)``."""
        self.set_status(SKIPPED)

    def submit(self):
        """Shortcut for ``set_status(SUBMITTED)``."""
        self.set_status(SUBMITTED)

    @classmethod
    def from_stack_name(cls, stack_name, context, requires=None, fn=None,
                        watch_func=None):
        """Create a step using only a stack name.

        Args:
            stack_name (str): Name of a CloudFormation stack.
            context (:class:`runway.cfngin.context.Context`): Context object.
                Required to initialize a "fake" :class:`runway.cfngin.stack.Stack`.
            requires (List[str]): Stacks that this stack depends on.
            fn (Callable): The function to run to execute the step.
                This function will be ran multiple times until the step
                is "done".
            watch_func (Callable): an optional function that will be
                called to "tail" the step action.

        Returns:
            :class:`Step`

        """
        from runway.cfngin.config import Stack as StackConfig
        from runway.cfngin.stack import Stack

        stack_def = StackConfig({'name': stack_name,
                                 'requires': requires or []})
        stack = Stack(stack_def, context)
        return cls(stack, fn=fn, watch_func=watch_func)

    @classmethod
    def from_persistent_graph(cls, graph_dict, context, fn=None,
                              watch_func=None):
        """Create a steps for a persistent graph dict.

        Args:
            graph_dict (Dict[str, List[str]]): A graph dict.
            context (:class:`runway.cfngin.context.Context`): Context object.
                Required to initialize a "fake" :class:`runway.cfngin.stack.Stack`.
            requires (List[str]): Stacks that this stack depends on.
            fn (Callable): The function to run to execute the step.
                This function will be ran multiple times until the step
                is "done".
            watch_func (Callable): an optional function that will be
                called to "tail" the step action.

        Returns:
            List[:class:`Step`]

        """
        steps = []

        for name, requires in graph_dict.items():
            steps.append(cls.from_stack_name(name, context, requires,
                                             fn, watch_func))
        return steps

    def __repr__(self):
        """Object represented as a string."""
        return "<CFNgin.plan.Step:%s>" % (self.stack.name,)

    def __str__(self):
        """Object displayed as a string."""
        return self.stack.name


class Graph(object):
    """Graph represents a graph of steps.

    The :class:`Graph` helps organize the steps needed to execute a particular
    action for a set of :class:`runway.cfngin.stack.Stack` objects. When
    initialized with a set of steps, it will first build a Directed Acyclic
    Graph from the steps and their dependencies.

    Attributes:
        dag (:class:`runway.cfngin.dag.DAG`): an optional
            :class:`runway.cfngin.dag.DAG` object. If one is not provided, a
            new one will be initialized.
        steps (Dict[str, :class:`Step`]): Dict with key of step name and
            value of :class:`Step`.

    Example:

    >>> dag = DAG()
    >>> a = Step("a", fn=build)
    >>> b = Step("b", fn=build)
    >>> dag.add_step(a)
    >>> dag.add_step(b)
    >>> dag.connect(a, b)

    """

    def __init__(self, steps=None, dag=None):
        """Instantiate class.

        Args:
            steps (Optional[Dict[str, :class:`Step`]]): Dict with key of step
                name and value of :class:`Step` for steps to initialize the
                Graph with. Note that if this is provided, a pre-configured
                :class:`runway.cfngin.dag.DAG` that already includes these
                steps should also be provided..
            dag (Optional[:class:`runway.cfngin.dag.DAG`]): An optional
                :class:`runway.cfngin.dag.DAG` object. If one is not provided,
                a new one will be initialized.

        """
        self.steps = steps or {}
        self.dag = dag or DAG()

    def add_step(self, step, add_dependencies=False, add_dependants=False):
        """Add a step to the graph.

        Args:
            step (:class:`Step`): The step to be added.
            add_dependencies (bool): Connect steps that need to be completed
                before this step.
            add_dependants (bool): Connect steps that require this step.

        """
        self.steps[step.name] = step
        self.dag.add_node(step.name)

        if add_dependencies:
            for dep in step.requires:
                self.connect(step.name, dep)

        if add_dependants:
            for parent in step.required_by:
                self.connect(parent, step.name)

    def add_step_if_not_exists(self, step, add_dependencies=False,
                               add_dependants=False):
        """Try to add a step to the graph.

        Can be used when failure to add is acceptable.

        Args:
            step (:class:`Step`): The step to be added.
            add_dependencies (bool): Connect steps that need to be completed
                before this step.
            add_dependants (bool): Connect steps that require this step.

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

    def add_steps(self, steps):
        """Add a list of steps.

        Args:
            steps (List[:class:`Step`]): The step to be added.

        """
        for step in steps:
            self.add_step(step)

        for step in steps:
            for dep in step.requires:
                self.connect(step.name, dep)

            for parent in step.required_by:
                self.connect(parent, step.name)

    def pop(self, step, default=None):
        """Remove a step from the graph.

        Args:
            step (:class:`Step`): The step to remove from the graph.
            default (Any): Returned if the step could not be popped

        Returns:
            Any

        """
        self.dag.delete_node_if_exists(step.name)
        return self.steps.pop(step.name, default)

    def connect(self, step, dep):
        """Connect a dependency to a step.

        Args:
            step (str): Step name to add a dependency to.
            dep (str): Name of dependent step.

        """
        try:
            self.dag.add_edge(step, dep)
        except KeyError as err:
            raise GraphError(err, step, dep)
        except DAGValidationError as err:
            raise GraphError(err, step, dep)

    def transitive_reduction(self):
        """Perform a transitive reduction on the underlying DAG.

        The transitive reduction of a graph is a graph with as few edges as
        possible with the same reachability as the original graph.

        See https://en.wikipedia.org/wiki/Transitive_reduction

        """
        self.dag.transitive_reduction()

    def walk(self, walker, walk_func):
        """Walk the steps of the graph.

        Args:
            walker (Callable[[:class:`runway.cfngin.dag.DAG`], Any]): Function
                used to walk the steps.
            walk_func (Callable[[:class:`Step`], Any]): Function called with a
                :class:`Step` as the only argument for each step of the plan.

        """
        def fn(step_name):
            """Get a step by step name and execute the ``walk_func`` on it.

            Args:
                step_name (str): Name of a step.

            """
            step = self.steps[step_name]
            return walk_func(step)

        return walker(self.dag, fn)

    def downstream(self, step_name):
        """Return the direct dependencies of the given step."""
        return list(self.steps[dep] for dep in self.dag.downstream(step_name))

    def transposed(self):
        """Return a "transposed" version of this graph.

        Useful for walking in reverse.

        """
        return Graph(steps=self.steps, dag=self.dag.transpose())

    def filtered(self, step_names):
        """Return a "filtered" version of this graph.

        Args:
            step_names (List[str]): Steps to filter.
        """
        return Graph(steps=self.steps, dag=self.dag.filter(step_names))

    def topological_sort(self):
        """Perform a topological sort of the underlying DAG.

        Returns:
            List[Step]

        """
        nodes = self.dag.topological_sort()
        return [self.steps[step_name] for step_name in nodes]

    def to_dict(self):
        """Return the underlying DAG as a dictionary."""
        return self.dag.graph

    def dumps(self, indent=None):
        """Output the graph as a json seralized string for storage.

        Args:
            indent (Optional[int]): Number of spaces for each indentation.

        Returns:
            str

        """
        return json.dumps(self.to_dict(), default=json_serial, indent=indent)

    @classmethod
    def from_dict(cls, graph_dict, context):
        """Create a Graph from a graph dict.

        Args:
            graph_dict (Dict[str, List[str]]): The dictionary used to
                create the graph.
            context (:class:`runway.cfngin.context.Context`): Required to init
                stacks.

        Returns:
            :class:`Graph`

        """
        return cls.from_steps(Step.from_persistent_graph(graph_dict, context))

    @classmethod
    def from_steps(cls, steps):
        """Create a Graph from Steps.

        Args:
            steps (List[:class:`Step`]): Steps used to create the graph.

        Returns:
            :class:`Graph`

        """
        graph = cls()
        graph.add_steps(steps)
        return graph

    def __str__(self):
        """Object displayed as a string."""
        return self.dumps()


class Plan(object):
    """A convenience class for working on a Graph.

    Attributes:
        context (:class:`runway.cfngin.context.Context`): Context object.
        description (str): Plan description.
        graph (Graph): Graph of the plan.
        id (str): UUID for the plan.
        reverse (bool): The graph has been transposed for walking in reverse.
        require_unlocked (bool): Require the persistent graph to be unlocked
            before executing steps.

    """

    def __init__(self, description, graph, context=None,
                 reverse=False, require_unlocked=True):
        """Initialize class.

        Args:
            description (str): Description of what the plan is going to do.
            graph (:class:`Graph`): Local graph used for the plan.
            context (:class:`runway.cfngin.context.Context`): Context object.
            reverse (bool): Transpose the graph for walking in reverse.
            require_unlocked (bool): Require the persistent graph to be
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
                nodes = []
                for target in self.context.stack_names:
                    if graph.steps.get(target):
                        nodes.append(target)
                graph = graph.filtered(nodes)
        else:
            self.locked = False

        self.graph = graph

    def outline(self, level=logging.INFO, message=""):
        """Print an outline of the actions the plan is going to take.

        The outline will represent the rough ordering of the steps that will be
        taken.

        Args:
            level (Optional[int]): a valid log level that should be used to log
                the outline
            message (Optional[str]): a message that will be logged to
                the user after the outline has been logged.

        """
        steps = 1
        LOGGER.log(level, "Plan \"%s\":", self.description)
        for step in self.steps:
            LOGGER.log(
                level,
                "  - step: %s: target: \"%s\", action: \"%s\"",
                steps,
                step.name,
                step.fn.__name__,
            )
            steps += 1

        if message:
            LOGGER.log(level, message)

    def dump(self, directory, context, provider=None):
        """Output the rendered blueprint for all stacks in the plan.

        Args:
            directory (str): Directory where files will be created.
            context (:class:`runway.cfngin.context.Contest`): Current CFNgin
                context.
            provider (:class:`runway.cfngin.providers.aws.default.Provider`):
                Provider to use when resolving the blueprints.

        """
        LOGGER.info("Dumping \"%s\"...", self.description)
        directory = os.path.expanduser(directory)
        if not os.path.exists(directory):
            os.makedirs(directory)

        def walk_func(step):
            """Walk function."""
            step.stack.resolve(
                context=context,
                provider=provider,
            )
            blueprint = step.stack.blueprint
            filename = stack_template_key_name(blueprint)
            path = os.path.join(directory, filename)

            blueprint_dir = os.path.dirname(path)
            if not os.path.exists(blueprint_dir):
                os.makedirs(blueprint_dir)

            LOGGER.info("Writing stack \"%s\" -> %s", step.name, path)
            with open(path, "w") as _file:
                _file.write(blueprint.rendered)

            return True

        return self.graph.walk(walk, walk_func)

    def execute(self, *args, **kwargs):
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

    def walk(self, walker):
        """Walk each step in the underlying graph, in topological order.

        Args:
            walker (func): a walker function to be passed to
                :class:`runway.cfngin.dag.DAG` to walk the graph.

        """
        def walk_func(step):
            """Execute a :class:`Step` wile walking the graph.

            Handles updating the persistent graph if one is being used.

            Args:
                step (:class:`Step`): :class:`Step` to execute.

            Returns:
                bool

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

            if (step.completed or
                    (step.skipped and
                     step.status.reason == ('does not exist in '
                                            'cloudformation'))):
                if step.fn.__name__ == '_destroy_stack':
                    self.context.persistent_graph.pop(step)
                    LOGGER.debug("Removed step '%s' from the persistent graph",
                                 step.name)
                elif step.fn.__name__ == '_launch_stack':
                    self.context.persistent_graph.add_step_if_not_exists(
                        step, add_dependencies=True, add_dependants=True
                    )
                    LOGGER.debug("Added step '%s' to the persistent graph",
                                 step.name)
                else:
                    return result
                self.context.put_persistent_graph(self.lock_code)
            return result

        return self.graph.walk(walker, walk_func)

    @property
    def lock_code(self):
        """Code to lock/unlock the persistent graph.

        Returns:
            str

        """
        return str(self.id)

    @property
    def steps(self):
        """Return a list of all steps in the plan.

        Returns:
            List[:class:`Step`]

        """
        steps = self.graph.topological_sort()
        steps.reverse()
        return steps

    @property
    def step_names(self):
        """Return a list of all step names.

        Returns:
            List[str]

        """
        return [step.name for step in self.steps]

    def keys(self):
        """Return a list of all step names.

        Returns:
            List[str]

        """
        return self.step_names
