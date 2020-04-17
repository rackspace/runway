"""CFNgin base action."""
import logging
import os
import sys
import threading

import botocore.exceptions

from ..dag import ThreadedWalker, UnlimitedSemaphore, walk
from ..exceptions import PlanFailed
from ..plan import Graph, Plan, Step, merge_graphs
from ..status import COMPLETE
from ..util import ensure_s3_bucket, get_s3_endpoint, stack_template_key_name

LOGGER = logging.getLogger(__name__)

# After submitting a stack update/create, this controls how long we'll wait
# between calls to DescribeStacks to check on it's status. Most stack updates
# take at least a couple minutes, so 30 seconds is pretty reasonable and inline
# with the suggested value in
# https://github.com/boto/botocore/blob/1.6.1/botocore/data/cloudformation/2010-05-15/waiters-2.json#L22
#
# This can be controlled via an environment variable, mostly for testing.
STACK_POLL_TIME = int(os.environ.get("CFNGIN_STACK_POLL_TIME", 30))


def build_walker(concurrency):
    """Return a function for waling a graph.

    Passed to :class:`runway.cfngin.plan.Plan` for walking the graph.

    If concurrency is 1 (no parallelism) this will return a simple topological
    walker that doesn't use any multithreading.

    If concurrency is 0, this will return a walker that will walk the graph as
    fast as the graph topology allows.

    If concurrency is greater than 1, it will return a walker that will only
    execute a maximum of concurrency steps at any given time.

    Args:
        concurrency (int): Number of threads to use while walking.

    Returns:
        Callable[..., Any]: Function to walk a :class:`runway.cfngin.dag.DAG`.

    """
    if concurrency == 1:
        return walk

    semaphore = UnlimitedSemaphore()
    if concurrency > 1:
        semaphore = threading.Semaphore(concurrency)

    return ThreadedWalker(semaphore).walk


def stack_template_url(bucket_name, blueprint, endpoint):
    """Produce an s3 url for a given blueprint.

    Args:
        bucket_name (str): The name of the S3 bucket where the resulting
            templates are stored.
        blueprint (:class:`runway.cfngin.blueprints.base.Blueprint`): The
            blueprint object to create the URL to.
        endpoint (str): The s3 endpoint used for the bucket.

    Returns:
        str: S3 URL.

    """
    key_name = stack_template_key_name(blueprint)
    return "%s/%s/%s" % (endpoint, bucket_name, key_name)


class BaseAction(object):
    """Actions perform the actual work of each Command.

    Each action is tied to a :class:`runway.cfngin.commands.stacker.base.BaseCommand`,
    and is responsible for building the :class:`runway.cfngin.plan.Plan` that
    will be executed to perform that command.

    Attributes:
        DESCRIPTION (str): Description used when creating a plan for an action.
        bucket_name (str): S3 bucket used by the action.
        bucket_region (str): AWS region where S3 bucket is located.
        cancel (threading.Event): Cancel handler.
        context (:class:`runway.cfngin.context.Context`): The context
            for the current run.
        provider_builder (Optional[BaseProviderBuilder]):
            An object that will build a provider that will be interacted
            with in order to perform the necessary actions.
        s3_conn (boto3.client.Client): Boto3 S3 client.

    """

    DESCRIPTION = 'Base action'

    def __init__(self, context, provider_builder=None, cancel=None):
        """Instantiate class.

        Args:
            context (:class:`runway.cfngin.context.Context`): The context
                for the current run.
            provider_builder (Optional[:class:`BaseProviderBuilder`]):
                An object that will build a provider that will be interacted
                with in order to perform the necessary actions.
            cancel (threading.Event): Cancel handler.

        """
        self.context = context
        self.provider_builder = provider_builder
        self.bucket_name = context.bucket_name
        self.cancel = cancel or threading.Event()
        self.bucket_region = context.config.cfngin_bucket_region
        if not self.bucket_region and provider_builder:
            self.bucket_region = provider_builder.region
        self.s3_conn = self.context.s3_conn

    @property
    def _stack_action(self):
        """Run against a step."""
        raise NotImplementedError

    @property
    def provider(self):
        """Return a generic provider using the default region.

        Used for running things like hooks.

        Returns:
            :class:`runway.cfngin.providers.base.BaseProvider`

        """
        return self.provider_builder.build()

    def build_provider(self, stack):
        """Build a :class:`runway.cfngin.providers.base.BaseProvider`.

        Args:
            stack (:class:`runway.cfngin.stack.Stack`): Stack the action will
                be executed on.

        Returns:
            :class:`runway.cfngin.providers.base.BaseProvider`: Suitable for
            operating on the given :class:`runway.cfngin.stack.Stack`.

        """
        return self.provider_builder.build(region=stack.region,
                                           profile=stack.profile)

    def ensure_cfn_bucket(self):
        """CloudFormation bucket where templates will be stored."""
        if self.bucket_name:
            ensure_s3_bucket(self.s3_conn,
                             self.bucket_name,
                             self.bucket_region)

    def execute(self, **kwargs):
        """Run the action with pre and post steps."""
        try:
            self.pre_run(**kwargs)
            self.run(**kwargs)
            self.post_run(**kwargs)
        except PlanFailed as err:
            LOGGER.error(str(err))
            sys.exit(1)

    def pre_run(self, **kwargs):
        """Perform steps before running the action."""

    def post_run(self, **kwargs):
        """Perform steps after running the action."""

    def run(self, **kwargs):
        """Abstract method for running the action."""
        raise NotImplementedError("Subclass must implement \"run\" method")

    def s3_stack_push(self, blueprint, force=False):
        """Push the rendered blueprint's template to S3.

        Verifies that the template doesn't already exist in S3 before
        pushing.

        Returns:
            str: URL to the template in S3.

        """
        key_name = stack_template_key_name(blueprint)
        template_url = self.stack_template_url(blueprint)
        try:
            template_exists = self.s3_conn.head_object(
                Bucket=self.bucket_name, Key=key_name) is not None
        except botocore.exceptions.ClientError as err:
            if err.response['Error']['Code'] == '404':
                template_exists = False
            else:
                raise

        if template_exists and not force:
            LOGGER.debug("Cloudformation template %s already exists.",
                         template_url)
            return template_url
        self.s3_conn.put_object(Bucket=self.bucket_name,
                                Key=key_name,
                                Body=blueprint.rendered,
                                ServerSideEncryption='AES256',
                                ACL='bucket-owner-full-control')
        LOGGER.debug("Blueprint %s pushed to %s.", blueprint.name,
                     template_url)
        return template_url

    def stack_template_url(self, blueprint):
        """S3 URL for CloudFormation template object.

        Returns:
            str

        """
        return stack_template_url(
            self.bucket_name, blueprint, get_s3_endpoint(self.s3_conn)
        )

    def _generate_plan(self, tail=False, reverse=False,
                       require_unlocked=True,
                       include_persistent_graph=False):
        """Create a plan for this action.

        Args:
            tail (Union[bool, Callable]): An optional function to call
                to tail the stack progress.
            reverse (bool): If True, execute the graph in reverse (useful for
                destroy actions).
            require_unlocked (bool): If the persistent graph is locked, an
                error is raised.
            include_persistent_graph (bool): Include the persistent graph
                in the :class:`runway.cfngin.plan.Plan` (if there is one).
                This will handle basic merging of the local and persistent
                graphs if an action does not require more complex logic.

        Returns:
            :class:`runway.cfngin.plan.Plan`: The resulting plan object

        """
        tail = self._tail_stack if tail else None

        def target_fn(*_args, **_kwargs):
            """Target function."""
            return COMPLETE

        steps = [
            Step(stack, fn=self._stack_action, watch_func=tail)
            for stack in self.context.get_stacks()]

        steps += [
            Step(target, fn=target_fn)
            for target in self.context.get_targets()]

        graph = Graph.from_steps(steps)

        if include_persistent_graph and self.context.persistent_graph:
            persist_steps = Step.from_persistent_graph(
                self.context.persistent_graph.to_dict(),
                self.context,
                fn=self._stack_action,
                watch_func=tail
            )
            persist_graph = Graph.from_steps(persist_steps)
            graph = merge_graphs(graph, persist_graph)

        return Plan(
            context=self.context,
            description=self.DESCRIPTION,
            graph=graph,
            reverse=reverse,
            require_unlocked=require_unlocked)

    def _tail_stack(self, stack, cancel, retries=0, **kwargs):
        """Tail a stack's event stream."""
        provider = self.build_provider(stack)
        return provider.tail_stack(stack, cancel, retries, **kwargs)
