"""Click options."""
# pylint: disable=invalid-name
import click

ci = click.option(
    "--ci",
    default=False,
    envvar="CI",
    is_flag=True,
    help="Run in non-interactive mode.",
)

debug = click.option(
    "--debug",
    count=True,
    envvar="DEBUG",
    help="Supply once to display Runway debug logs. "
    "Supply twice to display all debug logs.",
)

deploy_environment = click.option(
    "-e",
    "--deploy-environment",
    envvar="DEPLOY_ENVIRONMENT",
    metavar="<env-name>",
    help="Manually specify the name of the deploy environment.",
)

no_color = click.option(
    "--no-color",
    default=False,
    envvar="RUNWAY_NO_COLOR",
    is_flag=True,
    help="Disable color in Runway's logs.",
)

tags = click.option(
    "--tag",
    "tags",
    metavar="<tag>...",
    multiple=True,
    help="Select modules by tag or tags. "
    "This option can be specified more than once to build a"
    ' list of tags that are treated as "AND". '
    '(e.g. "--tag <tag1> --tag <tag2>" would select all modules'
    " with BOTH tags).",
)

verbose = click.option(
    "--verbose",
    default=False,
    envvar="VERBOSE",
    is_flag=True,
    help="Display Runway verbose logs.",
)
