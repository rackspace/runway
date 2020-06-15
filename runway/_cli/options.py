"""Click options."""
# pylint: disable=invalid-name
import click

deploy_environment = click.option('-e', '--deploy-environment',
                                  envvar='DEPLOY_ENVIRONMENT',
                                  metavar='<env-name>')
