"""Gets information on the CloudFormation stacks based on the given config."""
from ...actions import info
from .base import BaseCommand


class Info(BaseCommand):
    """Info subcommand."""

    name = "info"
    description = __doc__

    def add_arguments(self, parser):
        """Add arguments."""
        super(Info, self).add_arguments(parser)
        self._add_argument_stacks(parser)

    def run(self, options):
        """Run the command."""
        super(Info, self).run(options)
        action = info.Action(options.context, provider_builder=options.provider_builder)

        action.execute()

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
        return {"stack_names": options.stacks}
