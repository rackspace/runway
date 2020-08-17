"""Destroys CloudFormation stacks based on the given config.

CFNgin will determine the order in which stacks should be destroyed based on
any manual requirements they specify or output values they rely on from other
stacks.

"""
from ...actions import destroy
from .base import BaseCommand, cancel


class Destroy(BaseCommand):
    """Destroy subcommand."""

    name = "destroy"
    description = __doc__

    def add_arguments(self, parser):
        """Add arguments."""
        super(Destroy, self).add_arguments(parser)
        self._add_argument_max_parallel(parser)
        self._add_argument_tail(parser)
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Whether or not you want to go through with destroying the stacks",
        )
        parser.add_argument(
            "--targets",
            "--stacks",
            action="append",
            metavar="STACKNAME",
            type=str,
            help="Only work on the stacks given. Can be "
            "specified more than once. If not specified "
            "then CFNgin will work on all stacks in the "
            "config file.",
        )

    def run(self, options):
        """Run the command."""
        super(Destroy, self).run(options)
        action = destroy.Action(
            options.context, provider_builder=options.provider_builder, cancel=cancel()
        )
        action.execute(
            concurrency=options.max_parallel, force=options.force, tail=options.tail
        )

    def get_context_kwargs(self, options):
        """Return a dictionary of kwargs that will be used with the Context.

        This allows commands to pass in any specific arguments they define to
        the context.

        Args:
            options (:class:`argparse.Namespace`): arguments that have been
                passed via the command line

        Returns:
            Dict[str, Any]: Dictionary that will be passed to Context
            initializer as kwargs.

        """
        return {"stack_names": options.targets}
