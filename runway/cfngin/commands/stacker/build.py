"""Launches or updates CloudFormation stacks based on the given config.

CFNgin is smart enough to figure out if anything (the template or parameters)
have changed for a given stack. If nothing has changed, CFNgin will correctly
skip executing anything against the stack.

"""
from ...actions import build
from .base import BaseCommand, cancel


class Build(BaseCommand):
    """Build subcommand."""

    name = "build"
    description = __doc__

    def add_arguments(self, parser):
        """Add arguments."""
        super(Build, self).add_arguments(parser)
        self._add_argument_max_parallel(parser)
        self._add_argument_tail(parser)
        parser.add_argument(
            "-o",
            "--outline",
            action="store_true",
            help="Print an outline of what steps will be taken to build the stacks",
        )
        parser.add_argument(
            "--force",
            action="append",
            default=[],
            metavar="STACKNAME",
            type=str,
            help="If a stackname is provided to --force, it "
            "will be updated, even if it is locked in "
            "the config.",
        )
        parser.add_argument(
            "--targets",
            "--stacks",
            action="append",
            metavar="STACKNAME",
            type=str,
            help="Only work on the stacks given, and their "
            "dependencies. Can be specified more than "
            "once. If not specified then CFNgin will "
            "work on all stacks in the config file.",
        )
        parser.add_argument(
            "-d",
            "--dump",
            action="store",
            type=str,
            help="Dump the rendered Cloudformation templates to a directory",
        )

    def run(self, options):
        """Run the command."""
        super(Build, self).run(options)
        action = build.Action(
            options.context, provider_builder=options.provider_builder, cancel=cancel()
        )
        action.execute(
            concurrency=options.max_parallel,
            outline=options.outline,
            tail=options.tail,
            dump=options.dump,
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
        return {"stack_names": options.targets, "force_stacks": options.force}
