"""Click options."""

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
    help="Supply once to display Runway debug logs. Supply twice to display all debug logs.",
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

modules = click.option(
    "--module",
    "modules",
    metavar="<module-name>...",
    multiple=True,
    help="Select modules by name. Supports glob patterns (e.g., 'network-*'). "
    "This option can be specified more than once to select multiple modules. "
    '(e.g. "--module network-vpc --module app-*.cfn").',
)

stacks = click.option(
    "--stack",
    "stacks",
    metavar="<stack-name>...",
    multiple=True,
    help="Select CFNgin stacks by name within the targeted module(s). "
    "This option can be specified more than once to select multiple stacks. "
    "Only applies to CloudFormation/CFNgin modules. "
    '(e.g. "--stack vpc-stack --stack security-groups").',
)

create_changeset = click.option(
    "--create-changeset",
    "create_changeset",
    default=False,
    is_flag=True,
    help="Create and retain CloudFormation changesets instead of deleting them after showing diff. "
    "Outputs changeset IDs for use in CI/CD pipelines. "
    "Use with --output json for machine-readable output.",
)

changeset_output_format = click.option(
    "--output",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format for changeset information. Use 'json' for CI/CD integration.",
)

execute_changesets = click.option(
    "--execute-changesets",
    "changeset_file",
    type=click.Path(exists=True),
    metavar="<file>",
    help="Execute changesets from a JSON file created by 'runway plan --create-changeset'. "
    "Skips normal stack update logic and executes the pre-created changesets directly.",
)
