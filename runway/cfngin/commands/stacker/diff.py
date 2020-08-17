"""Diffs the config against the currently running CloudFormation stacks.

Sometimes small changes can have big impacts.  Run "cfngin diff" before
"cfngin build" to detect bad things(tm) from happening in advance!

"""
from ...actions import diff
from .base import BaseCommand


class Diff(BaseCommand):
    """Diff subcommand."""

    name = "diff"
    description = __doc__

    def add_arguments(self, parser):
        """Add arguments."""
        super(Diff, self).add_arguments(parser)
        self._add_argument_stacks(parser)
        parser.add_argument(
            "--force",
            action="append",
            default=[],
            metavar="STACKNAME",
            type=str,
            help="If a stackname is provided to --force, it "
            "will be diffed, even if it is locked in "
            "the config.",
        )

    def run(self, options):
        """Run the command."""
        super(Diff, self).run(options)
        action = diff.Action(options.context, provider_builder=options.provider_builder)
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
        return {"stack_names": options.stacks, "force_stacks": options.force}
