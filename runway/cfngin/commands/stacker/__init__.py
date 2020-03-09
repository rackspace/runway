"""CFNgin commands."""
import logging
import warnings

from runway.cfngin import __version__

from ... import session_cache
from ...config import render_parse_load as load_config
from ...context import Context
from ...providers.aws import default
from .base import BaseCommand
from .build import Build
from .destroy import Destroy
from .diff import Diff
from .graph import Graph
from .info import Info

LOGGER = logging.getLogger(__name__)


class Stacker(BaseCommand):
    """Stacker command."""

    name = "stacker"
    subcommands = (Build, Destroy, Info, Diff, Graph)

    DEPRECATION_MSG = ("Runway's Stacker CLI components have been deprecated "
                       "and will be removed in the next major release of "
                       "Runway.")

    def configure(self, options):
        """Configure CLI command."""
        warnings.warn(self.DEPRECATION_MSG, DeprecationWarning)
        LOGGER.warning(self.DEPRECATION_MSG)
        session_cache.default_profile = options.profile

        self.config = load_config(
            options.config.read(),
            environment=options.environment,
            validate=True,
        )

        options.provider_builder = default.ProviderBuilder(
            region=options.region,
            interactive=options.interactive,
            replacements_only=options.replacements_only,
            recreate_failed=options.recreate_failed,
            service_role=self.config.service_role,
        )

        options.context = Context(
            environment=options.environment,
            config=self.config,
            config_path=options.config.name,
            region=options.region,
            # Allow subcommands to provide any specific kwargs to the Context
            # that it wants.
            **options.get_context_kwargs(options)
        )

        super(Stacker, self).configure(options)
        if options.interactive:
            LOGGER.info("Using interactive AWS provider mode.")
        else:
            LOGGER.info("Using default AWS provider mode")

    def add_arguments(self, parser):
        """Add CLI arguments."""
        parser.add_argument("--version", action="version",
                            version="%%(prog)s %s" % (__version__,))
