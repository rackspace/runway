"""Click options."""
# pylint: disable=invalid-name
import click

ci = click.option('--ci',
                  default=False,
                  envvar='CI',
                  is_flag=True,
                  help='Run in noninteractive mode.')
deploy_environment = click.option('-e', '--deploy-environment',
                                  envvar='DEPLOY_ENVIRONMENT',
                                  metavar='<env-name>',
                                  help='Manually specify the name of the '
                                  'deploy environment.')
tags = click.option('--tag', 'tags',
                    metavar='<tag>...',
                    multiple=True,
                    help='Select modules by tag or tags. '
                    'This option can be specified more than once to build a'
                    ' list of tags that are treated as "AND". '
                    '(ex. "--tag <tag1> --tag <tag2>" would select all modules'
                    ' with BOTH tags).')
