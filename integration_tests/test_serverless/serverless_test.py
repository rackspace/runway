"""Re-usable class for Serverless testing."""
# pylint: disable=no-self-use
import os
import tempfile
from pathlib import Path

from integration_tests.test_serverless.test_serverless import Serverless
from integration_tests.utils import run_command
from runway.cfngin.hooks.staticsite.utils import get_hash_of_files

from runway.context import RunwayContext
from runway.core.providers import aws
from runway.module.serverless import get_src_hash
from runway.s3_utils import (
    download,
    get_matching_s3_keys,
    purge_and_delete_bucket,
    purge_bucket,
)
from runway.utils import change_dir, find_cfn_output


class ServerlessTest(Serverless):
    """Class for Serverless tests."""

    ENVS = ("dev", "test")

    def __init__(  # pylint: disable=super-init-not-called
        self, template, templates_dir, environment, logger
    ):
        """Initialize class."""
        self.ctx = RunwayContext()
        self.ctx.env.aws_region = "us-east-1"
        self.template_name = template
        self.templates_dir = templates_dir
        self.template_dir = os.path.join(templates_dir, template)
        self.environment = environment
        self.logger = logger
        self.runway_config_path = os.path.join(templates_dir, template, "runway.yml")

    def get_serverless_bucket(self, stack_name, session):
        """Get bucket created by serverless."""
        cfn_client = session.client("cloudformation")
        stacks = cfn_client.describe_stacks(StackName=stack_name)
        self.logger.debug("Found Stacks: ", stacks)
        return find_cfn_output(
            "ServerlessDeploymentBucketName", stacks["Stacks"][0]["Outputs"]
        )

    def get_promote_zip_bucket(self, runway_config):
        """Get promotezip bucket from runway config."""
        deployment = runway_config["deployments"][0]
        module = deployment.get("modules")[0]
        return module.get("options", {}).get("promotezip", {}).get("bucketname")

    def get_session(self, role_arn):
        """Get assumed role session."""
        self.logger.info("Assuming role: %s", role_arn)
        with aws.AssumeRole(
            self.ctx, role_arn=role_arn, session_name="runway-integration-tests"
        ) as assumed:
            # explicitly supply creds so when env vars are reverted,
            # assumed session is still valid
            return self.ctx.get_session(
                aws_access_key_id=assumed.credentials["AccessKeyId"],
                aws_secret_access_key=assumed.credentials["SecretAccessKey"],
                aws_session_token=assumed.credentials["SessionToken"],
                region="us-east-1",
            )

    def get_configs(self):
        """Get Runway and Serverless parsed configs."""
        return {
            "Runway": self.parse_config(os.path.join(self.template_dir, "runway.yml")),
            "Serverless": self.parse_config(
                os.path.join(self.template_dir, "serverless.yml")
            ),
        }

    def get_zip_hashes(self, env):
        """Get serverless and runway buckets."""
        configs = self.get_configs()
        promotezip_bucket = self.get_promote_zip_bucket(configs["Runway"])

        session = self.get_session(
            configs["Runway"]["deployments"][0].get("assume_role")["arn"]
        )
        sls_bucket = self.get_serverless_bucket(
            "-".join([configs["Serverless"].get("service"), env]), session
        )

        hashes = get_src_hash(configs["Serverless"], Path(self.template_dir))
        zip_dirs = {"Runway": tempfile.mkdtemp(), "Serverless": tempfile.mkdtemp()}
        for key, value in hashes.items():
            # don't need to pass session for promotezip bucket as it will use default
            # creds when downloading
            hash_zip = value + ".zip"
            func_zip = os.path.basename(key) + ".zip"
            self.logger.info("Download zip %s from %s", promotezip_bucket, hash_zip)
            download(
                promotezip_bucket, hash_zip, os.path.join(zip_dirs["Runway"], func_zip)
            )

            for s3key in get_matching_s3_keys(
                sls_bucket,
                "serverless/{0}/{1}".format(configs["Serverless"].get("service"), env),
                os.path.basename(key) + ".zip",
                session,
            ):
                self.logger.info("Downloading zip %s from %s", s3key, sls_bucket)
                # use session for this call as the bucket is in a different account
                download(
                    sls_bucket,
                    s3key,
                    os.path.join(zip_dirs["Serverless"], func_zip),
                    session,
                )

        return [get_hash_of_files(Path(v)) for _k, v in zip_dirs.items()]

    def run_runway(self, template, command="deploy"):
        """Deploy serverless template."""
        template_dir = os.path.join(self.templates_dir, template)
        if os.path.isdir(template_dir):
            self.logger.info(
                'Executing test "%s" in directory "%s"', template, template_dir
            )
            with change_dir(template_dir):
                self.logger.info('Running "runway %s" on %s', command, template_dir)
                return run_command(["runway", command], self.environment)
        else:
            self.logger.error("Directory not found: %s", template_dir)
            return 1

    def run(self):
        """Run tests."""
        self.clean()
        hashes = []
        for env in self.ENVS:
            self.set_environment(env)
            assert (
                self.run_runway(self.template_name) == 0
            ), "{}: Failed to deploy in {} environment".format(self.template_name, env)
            hashes.append(self.get_zip_hashes(env))

        self.logger.info("Verifying zips are the same")
        assert (
            hashes[1:] == hashes[:-1]
        ), "{}: Hash sums do not match for all zipped functions".format(
            self.template_name
        )

    def teardown(self):
        """Teardown any created resources."""
        self.logger.info("Tearing down: %s", self.template_name)
        configs = self.get_configs()

        for env in self.ENVS:
            self.set_environment(env)
            session = self.get_session(
                configs["Runway"]["deployments"][0].get("assume_role")["arn"]
            )
            sls_bucket = self.get_serverless_bucket(
                "-".join([configs["Serverless"].get("service"), env]), session
            )
            purge_bucket(sls_bucket, session=session)
            self.run_runway(self.template_name, "destroy")

        purge_and_delete_bucket(self.get_promote_zip_bucket(configs["Runway"]))
        self.clean()
