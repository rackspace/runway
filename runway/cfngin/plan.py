"""CFNgin plan, plan componenets, and functions for interacting with a plan."""
import logging
import os
import threading
import time
import uuid

from .dag import DAG, DAGValidationError, walk
from .exceptions import GraphError, PlanFailed
from .status import COMPLETE, FAILED, PENDING, SKIPPED, SUBMITTED, FailedStatus
from .ui import ui
from .util import stack_template_key_name

LOGGER = logging.getLogger(__name__)

COLOR_CODES = {
    SUBMITTED.code: 33,  # yellow
    COMPLETE.code: 32,   # green
    FAILED.code: 31,     # red
}


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


class Step(object):
    """State machine for executing generic actions related to stacks.

    Attributes:
        fn (Callable): the function to run to execute the step. This
            function will be ran multiple times until the step is "done".
        last_updated (float): Time when the step was last updated.
        stack (:class:`runway.cfngin.stack.Stack`): the stack associated with
            this step
        status (:class:`runway.cfngin.status.Status`): The status of step.
        watch_func (Callable): an optional function that will be called to
            "tail" the step action.

    """

    def __init__(self, stack, fn, watch_func=None):
        """Instantiate class.

        Args:
            stack (:class:`runway.cfngin.stack.Stack`): the stack associated
                with this step
            fn (Callable): the function to run to execute the step. This
                function will be ran multiple times until the step is "done".
            watch_func (Callable): an optional function that will be called to
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

    def __repr__(self):
        """Object represented as a string."""
        return "<CFNgin.plan.Step:%s>" % (self.stack.name,)

    def __str__(self):
        """Object displayed as a string."""
        return self.stack.name


def build_plan(description, graph,
               targets=None, reverse=False):
    """Build a plan from a list of steps.

    Args:
        description (str): an arbitrary string to
            describe the plan.
        graph (:class:`Graph`): a list of :class:`Graph` to execute.
        targets (list): an optional list of step names to filter the graph to.
            If provided, only these steps, and their transitive dependencies
            will be executed. If no targets are specified, every node in the
            graph will be executed.
        reverse (bool): If provided, the graph will be walked in reverse order
            (dependencies last).

    Returns:
        :class:`Plan`

    """
    # If we want to execute the plan in reverse (e.g. Destroy), transpose the
    # graph.
    if reverse:
        graph = graph.transposed()

    # If we only want to build a specific target, filter the graph.
    if targets:
        nodes = []
        for target in targets:
            for _, step in graph.steps.items():
                if step.name == target:
                    nodes.append(step.name)
        graph = graph.filtered(nodes)

    return Plan(description=description, graph=graph)


def build_graph(steps):
    """Build a graph of steps.

    Args:
        steps (List[:class:`Step`]): A list of :class:`Step` objects to
            execute.

    Returns:
        :class:`Graph`

    """
    graph = Graph()

    for step in steps:
        graph.add_step(step)

    for step in steps:
        for dep in step.requires:
            graph.connect(step.name, dep)

        for parent in step.required_by:
            graph.connect(parent, step.name)

    return graph


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
        steps (Dict[str, :class:`Step`]): an optional list of :class:`Step`
            objects to execute.

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

    def add_step(self, step):
        """Add a step to the graph.

        Args:
            step (:class:`Step`): Step to be added to the graph.

        """
        self.steps[step.name] = step
        self.dag.add_node(step.name)

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


class Plan(object):
    """A convenience class for working on a Graph.

    Attributes:
        description (str): Plan description.
        graph (Graph): Graph of the plan.
        id (str): UUID for the plan.

    """

    def __init__(self, description, graph):
        """Instantiate class.

        Args:
            description (str): description of the plan.
            graph (:class:`Graph`): a graph of steps.

        """
        self.id = uuid.uuid4()
        self.description = description
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
            PlanFailed: Raised if any of the steps fail.

        """
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
            """Walk function."""
            # Before we execute the step, we need to ensure that it's
            # transitive dependencies are all in an "ok" state. If not, we
            # won't execute this step.
            for dep in self.graph.downstream(step.name):
                if not dep.ok:
                    step.set_status(FailedStatus("dependency has failed"))
                    return step.ok

            return step.run()

        return self.graph.walk(walker, walk_func)

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
