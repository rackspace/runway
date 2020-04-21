# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.7.2] - 2020-04-21
### Fixed
- Maintenance release for GitHub Actions update

## [1.7.1] - 2020-04-21
### Fixed
- Maintenance release for GitHub Actions update

## [1.7.0] - 2020-04-21
### Added
- prompt to optionally provide an explicit deploy environment when git branch name is unexpected (e.g. feature branch) when run interactively

### Changed
- deprecated support for python 3.5
  - no longer testing for compatibility
  - not advertised as being supported

### Fixed
- cfngin `hook_data` is once again stored as a `dict` rather than `MutableMap` to support stacker hooks/lookups/blueprints that do not handle the `MutableMap` data type when consuming hook_data.

## [1.6.1] - 2020-04-14
### Fixed
- global variables in hooks are now reloaded between uses to mimic functionality present in `>1.5.0`

## [1.6.0] - 2020-04-07
### Fixed
- lookups are now resolved when using the `runway envvars` command
- Terraform list parameters from runway.yml will now properly formatted
- stacker's cli components can once again be used within CFNgin sessions by the inherited utility functions that require it

## Added
- ACM CloudFormation hook

## [1.5.2] - 2020-04-02
### Fixed
- `runway plan` for cfngin modules will now properly resolve output lookups when the original stack did not change or the reference stack is `locked: true`
- `env_var` deployment/module will now work as expected when used with a CFNgin or staticsite module
- when rendering a CFNgin config file, it should no longer raise an error if there is an undefined variable in a comment

## [1.5.1] - 2020-03-25
### Changed
- (binary/npm versions only) bumped embedded awacs version to v0.9.8

## [1.5.0] - 2020-03-24
### Added
- `runway.cfngin.cfngin.CFNgin` class (can also be imported as `runway.cfngin.CFNgin`)
- `runway.cfngin.context.Context.get_session()` method for creating a boto3 session using the correct AWS credentials
- `environment` and `region` as _common parameters_ for cloudformation modules so they do not need to be defined
  - pulled from the Runway context object
- `ssm` lookup usable in Runway and CFNgin config files
- `troposphere` transform option for lookups
- Private (authorized AKA Auth@Edge) static sites
- `termination_protection` CFNgin stack option

### Changed
- `get_session` can now accept AWS credentials when creating a thread-safe session
- Runway environment variable options to pull from `self.env_var` instead of `os.environ`
- deprecated the `run-stacker` command
- deprecated the use `get_session` directly when credentials are in environment variables
- deprecated `runway.cfngin.util.get_config_directory()` which was only used for the aws_lambda hook.
- deprecated Stacker CLI components
- deprecate `ssmstore` lookup
- deprecate `staticsite_acmcert_ssm_param` option
- deprecate `terraform_backend_ssm_params` option
- `hook_data` lookup now supports the standardized lookup query syntax
  - supports `load`, `transform`, `get`, and `default` arguments
  - dot notation to get nested data from the dictionary
- deprecate `stacker_bucket` in CFNgin configs
  - replaced by `cfngin_bucket`
- deprecate `stacker_bucket_region` in CFNgin configs
  - replaced by `cfngin_bucket_region`
- deprecate `stacker_cache_dir` in CFNgin configs
  - replaced by `cfngin_cache_dir`

### Fixed
- git module path will now default to the root of the repo when no `location` is provided.
- cfngin correctly notifies when a stack will be deleted during `runway plan` when using persistent graph

## [1.4.4] - 2020-02-28
### Fixed
- explicitly pass `provider` as a kwarg for resolving complex variable types
- error message raised when `var` lookup query is not in variables now includes the query
- `variables` is now passed from the config file to the `VariablesDefinition` as intended

## [1.4.3] - 2020-02-25
### Fixed
- CFN variable value lookup regression

### Added
- `RUNWAY_MAX_CONCURRENT_MODULES` configuration via environment variable
- `RUNWAY_MAX_CONCURRENT_REGIONS` configuration via environment variable

## [1.4.2] - 2020-02-21
### Fixed
- `runway.cfngin.commands.__init__` import of `__version__` through the stacker shim
- `stacker.variables` import error by adding a shim to `runway.variables`

## [1.4.1] - 2020-02-20
### Fixed
- `stacker.__version__` check when shimmed to CFNgin
- npm install on older nodejs versions

## [1.4.0] - 2020-02-18
### Added
- Add static site examples for React & Angular
- variable resolution in the runway config file
  - uses lookups to resolve value
    - resolves from environment variables, variables file, or variables definition
    - lookups can take arguments in addition to a query
      - parsing is part of the base class to standardize syntax
      - used to provide default values if the query fails and/or transform the data
  - only resolvable in specific areas of the config file (see docs for details)
  - some environment variables can only be used during processing of a module since they are set during processing
- `variables` top-level directive to the runway config file
  - explicitly define the path/name to a variables file instead of using the default path/names
  - define variables directly in the runway config file
    - if this is used with a variables file, what is defined in the runway config takes precedence
- `parameters` directive for modules and deployments
  - predecessor to `environments.$DEPLOY_ENVIRONMENT` map
- Add `args` option for serverless module to pass additional arguments/option to the serverless command

### Changed
- install now requires `pyhcl~=0.4` which is being used in place of the embedded copy
- `runway.embedded.stacker` is now `runway.cfngin`
- imports of stacker by anything run/deployed by runway will be redirected to `runway.cfngin`
- e.g. `from stacker.blueprints.base import Blueprint` will act as `from runway.cfngin.blueprints.base import Blueprint`
- `.cfn` modules no longer require `deployments[].environments.$DEPLOY_ENVIRONMENT` to be deployed when opting to not use a `$DEPLOY_ENVIRONMENT-$AWS_REGION.env` file if variables/lookups are used
- modules no longer require `deployments[].environments.$DEPLOY_ENVIRONMENT` to be deployed when opting to not use an environment specific variables file (.e.g `$DEPLOY_ENVIRONMENT-$AWS_REGION.env`) if `parameters` are used.
- `environments` key now acts as an explict toggle (with a booleon value per environment name, string of `$ACCOUNT_ID/$REGION`, or list of strings) for deploying modules to an environment
  - support old functionallity retained for the time being by merging into `parameters`

### Removed
- embedded `hcl`
- python 2.6 support for `PyYAML` and `cfn_flip` dependencies

### Fixed
- pinned `zipp` sub dependency to `~=1.0.0` to retain support for python 3.5
- `PyYAML` dependency is now `>=4.1,<5.3` to match the top-end of newer versions of `awscli`
- `NoSuchBucket` during `PutBucketEncryption` when sls tries to create a `promotezip` bucket
- `parallel_regions` causing subsequent deployments to be skipped

## [1.3.7] - 2020-01-07
### Fixed
- pinned `pyhcl` to `<0.3.14`
  - `0.3.14` vendored ply instead of having it as a dependency which breaks our embedded, patched copy

## [1.3.6] - 2019-12-28
### Fixed
- Correct detection of Serverless Framework projects with a JS config file

## [1.3.5] - 2019-12-19
### Fixed
- Updated `sls-py` sample to work properly w/ python plugin static caching
- Updated `k8s-tf` sample:
  - Python 2 compatibility for cert certificate script
  - kubeconfig file is now updated/recreated automatically

### Changed
- Updated `k8s-tf` sample:
  - Moved worker nodes to EKS node group

## [1.3.4] - 2019-12-18
### Fixed
- Fixed multi-stack CDK apps

### Added
- Allow single-binary use of bundled yamllint

### Changed
- `DEPLOY_ENVIRONMENT` is available to all module deployments as an environment variable
  - if it does not exist in the current environment, value is derived from branch or directory name
- Updated static site CFN template to use node v10 for path rewrite lambda
- embedded stacker will not resolve dependencies for `locked` stacks when they rely on other stacks
  - accepted upstream in <https://github.com/cloudtools/stacker/pull/746>

## [1.3.3] - 2019-11-26
### Changed
- Updated `runway test` error message to give direction on next steps when no tests are defined

## [1.3.2] - 2019-11-22
### Fixed
- `run-python` subcommand now supports most python files

## [1.3.1] - 2019-11-19
### Fixed
- Deployment selection regression from v1.3

## [1.3.0] - 2019-11-15
### Fixed
- `gen-sample cdk-py` now correctly generates a sample instead of trying to copy files that don't exist

### Added
- parallel region execution
  - `deployments[].regions.parallel[]` similar to parallel modules **OR**
  - `deployments[].parallel_regions[]` which is what the above translates to
  - cannot use parallel and non-parallel regions in the same deployment
  - requires `CI` mode and python >3

## [1.2.1] - 2019-11-13
### Fixed
- `--tag` docopt option to plan and updated docs
  - the backend already supports/handles this option. now docopt will allow it to be provided.

## [1.2.0] - 2019-11-12
### Added
- Terraform list/map variables can now be provided via runway.yml environment values

### Changed
- Updated python serverless sample generator to py3

### Fixed
- Better gen-sample output of available sample generators

## [1.1.0] - 2019-10-31
### Added
- Pre-module environment-variable overrides

## [1.0.3] - 2019-10-30
### Fixed
- Python 2 install

## [1.0.1] - 2019-10-30
### Fixed
- npm-based install (org-scoped package error)

## [1.0.0] - 2019-10-30
### Fixed
- Fix cross-platform subprocess execution (e.g. yarn specified without a file extension in staticsite build_steps)
- Better error messages for subprocess commands that fail to run
- cloudformation modules now ignore `docker-compose.yml` in the root of the module directory
- `diff` run against CloudFormation modules will now correctly handle missing/dependent stacks
- Environment detection from git branches will now fail gracefully when in a detached-HEAD state

### Added
- run-python & run-stacker commands (for single-binary compatibility)
- Custom error responses support for static sites
- `--tag <tag>...` option for deploy/destroy
  - select modules based on a list of tags applied in the runway file (ex. `deployments[].modules[].tags[]`)
  - can be used to construct a list of tags a module must have to be selected
- Terraform backend lookup via SSM params
- class for handling the runway config file that warns on invalid keys
- new top level `tests` to the runway config for user defined tests (cfn-lint, script, and yamllint)
- alternative runway config file name `runway.yaml`
- run-aws command (for awscli use in single-binary mode)
- tfenv and kbenv commands (for installing terraform/kubectl prior to a runway deployment)
- envvars command (for setting shell variables from environment variables defined in runway.yml)
- Kubernetes support (for kustomize-organized configurations)
- Parallel module execution
- single-binary build and the pipeline to support it
- serverless framework zip promotion support (e.g. build app once, reuse in multiple environments automatically)

### Removed
- _default_ tests. trying to run the test command with no tests defined will now result in an error.
- chef, flake8, pylint, and stacker blueprint tests (for single-binary compatibility)
- `SKIP_TF_GET` environment variable option for Terraform modules
- `gitclean` subcommand (rarely used and functionality is trivial to replicate in other scripts)

### Changed
- Terraform initialization should be considerably faster via use of `init --reconfigure`
- Updated CDK typescript sample generator to v1 syntax
- Terraform variables from runway.yml passed as environment variables (fixes <https://github.com/hashicorp/terraform/issues/19424#issuecomment-472186386>)
- CDK/Serverless `npm ci` skip option (formerly `skip-npm-ci`) moved to module options
- Top-level & deployment options now consistently documented with underscores (e.g. `account_id:` vs `account-id:`).

## [0.47.1] - 2019-07-19
### Fixed
- Workaround PyHCL error on empty files

## [0.47.0] - 2019-07-19
### Added
- Terraform 0.12 support

## [0.46.6] - 2019-07-08
### Added
- requirement for `pydocstyle<=3.0.0`

## [0.46.5] - 2019-06-04
### Fixed
- Fix PyYAML dependency issue on new installs
- Serverless string handling cosmetic error during destroy

## [0.46.4] - 2019-05-16
### Fixed
- Add CAPABILITY_AUTO_EXPAND capability to CFN deployments for macro support

## [0.46.3] - 2019-05-15
### Fixed
- Stop troposphere deprecation warnings on 2.4.2+
- Re-add `terraform init` execution after workspace switches
  - This appears to be required to ensure all plugins are downloaded

## [0.46.2] - 2019-05-13
### Fixed
- Better error handling during Terraform downloads

## [0.46.1] - 2019-05-01
### Fixed
- Terraform platform being incorrectly detected on Windows

## [0.46.0] - 2019-04-20
### Added
- In-app Terraform management (no longer needs to be downloaded separately)
- Terraform backend config lookup from CloudFormation

### Fixed
- Fix Terraform module not detecting backend config changes
- Remove unnecessary `terraform init` executions after workspace switches
- Catch failed `terraform init` executions on subsequent plan/deploys

### Changed
- Add warning about incorrect AWS_PROFILE environment variable usage with Serverless/CDK

## [0.45.4] - 2019-04-13
### Fixed
- Stacker `cleanup_s3` hook `bucket_name` option

### Changed
- Add warning about missing tfenv on Windows

## [0.45.3] - 2019-04-10
### Fixed
- Fixed CFN module detection with no env files

## [0.45.2] - 2019-04-08
### Changed
- Update stacker to v1.7

## [0.45.1] - 2019-04-03
### Fixed
- Correct test command invocation bug introduced in 0.45

## [0.45.0] - 2019-04-02
### Changed
- Add optional deployment names
- Update TypeScript CDK sample generator
- Cleanup command class code

### Added
- Support CDK context values
- Python CDK sample generator
- C# CDK sample generator

### Fixed
- Support terraform sample generator use directly from git master

## [0.44.3] - 2019-03-26
### Fixed
- Ensure PyYaml.load is not used (work around CVE-2017-18342)

## [0.44.2] - 2019-03-21
### Fixed
- Fixed module config options completely overriding deployment options
  - Options will now be deeply merged, allowing selective overrides per-module

## [0.44.1] - 2019-03-16
### Fixed
- Corrected bug in module selection

## [0.44.0] - 2019-03-11
### Changed
- Output environment message only once on startup
- Improve deployment progress messages

## [0.43.0] - 2019-03-07
### Added
- Add module_options deployment parameter for shared module options
- Support Terraform backend config via Runway module options

## [0.42.0] - 2019-03-06
### Fixed
- Correct install issue with latest PyYAML beta release

### Added
- New Serverless Typescript sample module template

## [0.41.2] - 2019-03-05
- Catch invalid deployment section input

## [0.41.1] - 2019-02-28
### Fixed
- Correct Terraform workspace creation/selection with custom backend keys

## [0.41.0] - 2019-02-22
### Fixed
- Correct Terraform workspace creation/selection with custom backend keys

### Added
- Update embedded stacker to v1.6 w/ Jinja2 templating

## [0.40.1] - 2019-01-15
### Fixed
- Fixed staticsite module use with troposphere 2.4+

## [0.40.0] - 2019-01-11
### Added
- Optional cfn-lint template checking

### Changed
- Removed check for python blueprint execute status
  - This doesn't really fit with current recommendation to execute environments under pipenv

## [0.39.1] - 2018-12-28
### Fixed
- Remove default yamllint truthy check to allow yes/no values

## [0.39.0] - 2018-12-27
### Added
- CFN SSM parameter types

## [0.38.2] - 2018-12-21
### Fixed
- Support `.yamllint` filename (in addition to `.yamllint.yml`) for yamllint customization

## [0.38.1] - 2018-12-19
### Fixed
- Additional Windows npm/npx command fixes

## [0.38.0] - 2018-12-19
### Fixed
- Additional Windows npm/npx command fixes

### Added
- Incorporate stacker typo & stack rollback fixes

## [0.37.2] - 2018-12-19
### Fixed
- Fix file detection on Windows (find `npm.cmd`)

## [0.37.1] - 2018-12-11
### Fixed
- Fix embedded stacker aws_lambda hook file permissions

## [0.37.0] - 2018-12-03
### Added
- New `init` command for generating runway.yml

### Changed
- Updated cfn gen-sample to deploy tf state bucket (matching stacker sample)

## [0.36.0] - 2018-11-21
### Fixed
- Documentation cleanup

### Added
- New staticsite_lambda_function_associations Static Site module option

## [0.35.3] - 2018-11-16
### Fixed
- Add egg files to source packaging (i.e. fix easy_install installs)

## [0.35.2] - 2018-11-05
### Fixed
- Improve approval resiliency on CFN stack updates (Stacker #674)

## [0.35.1] - 2018-11-01
### Fixed
- Added error message when a deployment specifies no regions

## [0.35.0] - 2018-11-01
### Added
- CloudFormation modules can now locally reference other CloudFormation modules

## [0.34.0] - 2018-10-24
### Added
- CloudFormation config deployments will now log the region to which they are deployed

### Changed
- Embedded embedded stacker to v1.5

## [0.33.0] - 2018-10-09
### Added
- Environment variable values can now be specified as relative or absolute paths (via yaml lists) in addition to regular strings

## [0.32.0] - 2018-10-08
### Added
- Added per-environment, per-deployment environment variable values

## [0.31.2] - 2018-10-04
### Fixed
- Fixed stacker execution in virtualenvs on Windows

## [0.31.1] - 2018-10-03
### Fixed
- Fixed executable detection on Windows

## [0.31.0] - 2018-10-01
### Added
- Add clear logging of each module being processed

## [0.30.0] - 2018-10-01
### Added
- Add AWS CDK support

### Fixed
- Destroys on Serverless modules will no longer exit code 1 if the destroy has been run previously.

## [0.29.6] - 2018-09-24
### Fixed
- Fix `current_dir` deployment option

## [0.29.5] - 2018-09-19
### Fixed
- Re-initialize Terraform modules after workspace switching (ensure providers are downloaded)

## [0.29.4] - 2018-09-18
### Fixed
- Avoid error when assume-role config does not specify a role for the current environment

## [0.29.3] - 2018-09-04
### Fixed
- Update dependencies to prevent pip errors

## [0.29.2] - 2018-09-04
### Fixed
- Fixed skip-npm-ci option

## [0.29.1] - 2018-09-04
### Fixed
- Update embedded stacker to fix interactive CFN stack updates with empty string parameters

## [0.29.0] - 2018-08-28
### Added
- Static sites archives will now be automatically pruned (keeping only the 15 latest)

## [0.28.0] - 2018-08-27
### Added
- Static sites can now use Lambda@Edge to support default directory indexes (e.g. example.org/foo/)

### Fixed
- Fixed stacker git remote package support on Python 3
- Static site modules will no longer error when an environment config is missing

## [0.27.1] - 2018-08-21
### Fixed
- Fixed module options regression introduced in v0.25

## [0.27.0] - 2018-08-20
### Added
- Support SSM Parameters for static site module ACM cert ARN lookups

## [0.26.0] - 2018-08-20
### Added
- Basic documentation for gen-sample commands

### Changed
- Update Stacker sample module with Terraform-supporting template

## [0.25.0] - 2018-08-17
### Added
- Allow environments to be specified at top level of deployment

## [0.24.0] - 2018-08-17
### Fixed
- Additional Python 3 fixes (check_output bytes -> str decoding)

### Added
- Static website deployment module
- Module options in runway.yaml (or runway.module.yaml in a module)
  - These can be used to make Terraform, Serverless, and CloudFormation (Stacker) variable/environment files optional.

### Changed
- Only use `npm ci` when `CI` environment variable is set

## [0.23.3] - 2018-08-08
### Changed
- Sync v0.23.2 change w/ [upstream patch](https://github.com/cloudtools/stacker/pull/646)

## [0.23.2] - 2018-08-08
### Fixed
- Fixed CloudFormation file lookups (Stacker [issue #645](https://github.com/cloudtools/stacker/issues/645))

## [0.23.1] - 2018-08-07
### Fixed
- Fixed CFN stack deployments with unspecified parameters (UsePreviousValue)

## [0.23.0] - 2018-08-06
### Added
- Python 3 support
- Updated embedded Stacker to v1.4

## [0.22.3] - 2018-08-03
### Fixed
- Suppress runway stacktraces when terraform setup commands fail

## [0.22.2] - 2018-07-27
### Fixed
- Skip attempt at pylint during preflight when no python files are detected

## [0.22.1] - 2018-07-27
### Added
- Adding debugging statements prior to pylint runs

## [0.22.0] - 2018-07-24
### Fixed
- It is now possible to disable pylint error checks in a custom .pylintrc
- Pylint is now only instantiated one for all file checks
  - This fixes duplicate code checking and should greatly speed up tests

### Added
- Added reference .pylintrc to templates

## [0.21.0] - 2018-07-19
### Fixed
- Debug logging now properly invoked across all commands
- CFN deployments run in debug mode will display the exact Stacker command being run

## [0.20.7] - 2018-07-16
### Fixed
- Restrict pylint version dependency to match Runway's Python 2 requirement

## [0.20.5] - 2018-06-25
### Fixed
- Add prompt before initiating `destroy` when only one deployment configured

## [0.20.4] - 2018-06-25
### Fixed
- Suppress stacktrace when stacker/terraform/serverless fail
  - They provide their own error messages/stacktrace; runway errors just obfuscate them
- Fix 0.20.1 regression of global stacker install use (instead of embedded version)

## [0.20.3] - 2018-06-13
### Fixed
- Fix stacker invocation error introduced in v0.20.1

## [0.20.1] - 2018-06-13
### Fixed
- Multiple CFN modules can now use the same remote Stacker package at different versions
  - Previously, the first module to load a remote package (e.g. stacker_blueprints at tag v1.0.3) would have that tagged version stuck for the rest of the runway deployment. Now, subsequent modules can specify other tags/commits/etc of the same remote package.

## [0.20.0] - 2018-06-11
### Added
- Add `duration` option to assume role operations

## [0.19.0] - 2018-06-08
### Fixed
- Remove duplicate stacker logging output
- Bypass CFN blueprint file execution mode check on Windows

### Changed
- Update embedded stacker to v1.3
- Add stacker as a requirement of runway
  - This should provide a better experience for user IDEs when editing stacker blueprints

## [0.18.0] - 2018-06-05
### Added
- Add `.terraform-version` file to terraform sample module

## [0.17.0] - 2018-05-23
### Added
- Add `skip-npm-ci` deployment option

## [0.16.0] - 2018-05-23
### Added
- Add `env/` directory option for SLS variable files

## [0.15.3] - 2018-05-17
### Fixed
- Set AWS_REGION environment var in addition to AWS_DEFAULT_REGION for modules.

## [0.15.2] - 2018-05-17
### Fixed
- Fix `stacker-runway` command error on importing Stacker before syspath update

## [0.15.1] - 2018-05-17
### Fixed
- Allow use of `whichenv` command in module directories

## [0.15.0] - 2018-05-17
### Added
- Add `whichenv` command

## [0.14.3] - 2018-05-14
### Fixed
- Properly reverse order of CFN stack config files during dismantle

## [0.14.2] - 2018-05-03
### Fixed
- Sync stacker invocation w/ upstream stacker script

## [0.14.1] - 2018-04-30
### Fixed
- Corrected 0.14 error causing yamllint to not run

## [0.14.0] - 2018-04-24
### Changed
- Serverless modules no longer require a `sls` script
- CloudFormation modules will no longer treat hidden files (files prefixed with a period) as stack configuration files (i.e. `.gitlab-ci.yml` will be ignored)

## [0.13.0] - 2018-04-23
### Fixed
- Flake8 now correctly exits non-zero on errors

### Changed
- Add support for environment `.flake8` config files

## [0.12.3] - 2018-04-16
### Fixed
- Fix stacker-runway command execution
- Fix yamllint including remote terraform modules

## [0.12.2] - 2018-04-04
### Fixed
- Fix Cloudformation environment file name options (now correctly supports ENV-REGION.env & ENV.env)

## [0.12.1] - 2018-04-02
### Changed
- Rename `account-id` and `account-alias` to match `assume-role` hyphen use

## [0.12.0] - 2018-04-02
### Changed
- Drop support for generic `backend.tfvars` terraform backend config
  - Any previous `backend.tfvars` values should be moved into the primary (e.g. main.tf) backend config
- On destroy/dismantle, reverse order of deployments and their contained modules
- Add `account_id` and `account_alias` deployment config options for account verification
- Add support for [tfenv](https://github.com/kamatama41/tfenv)
- Update terraform sample template to use a region-specific backend

### Fixed
- Fix Terraform backend initialization when switching backend configs
- Exclude .serverless directory from `runway test/preflight`
- Lower botocore logging messages (to pre v0.11.0 levels)

## [0.11.1] - 2018-03-22
### Changed
- Fix missed embedded stacker v1.2 script update

## [0.11.0] - 2018-03-22
### Changed
- Updated embedded Stacker to v1.2

## [0.10.0] - 2018-03-21
### Added
- Runway now has a `destroy`/`dismantle` command for removing deployments

### Changed
- Fixed errors with embedded `runway-stacker` script not setting the proper sys.path

## [0.9.1] - 2018-03-15
### Changed
- Update Terraform sample template to bump aws provider version from ~>v0.1 to ~>v1.0

## [0.9.0] - 2018-03-15
### Changed
- Allow per-environment assume-role ARNs.
- Add additional logging messages during `preflight` to clarify checks being performed.
- Add yaml & python checking to files at root of env (i.e. for use with `current_dir: true`)
- Drop legacy check for 'Makefile.py' executable status

## [0.8.0] - 2018-03-12
### Changed
- Change Serverless `sls deploy` run-script to just `sls`
  - This is necessary for the upcoming `destroy`/`dismantle` (e.g. `sls remove`) support
- Automatically use `npm ci` if available

### Fixed
- Fixed broken assume-role capability.
- Remove erroneous Serverless `.yaml` variables file extension.

## [0.7.0] - 2018-03-02
### Changed
- Make `current_dir` & `ignore_git_branch` options work together more intuitively (now doesn't require nested module directories)

## [0.6.2] - 2018-02-28
### Changed
- Bump boto3/botocore dependencies to work around pip dependency resolution (removes the need to manually upgrade botocore after installation on Amazon Linux).

## [0.6.1] - 2018-02-27
### Changed
- Add helper message when CloudFormation templates are incorrectly placed alongside stack config files.

## [0.6.0] - 2018-02-26
### Changed
- Override module-type autodetection when README-recommended module suffixes are used.

## [0.5.1] - 2018-02-26
### Changed
- Fix missing colorama runtime dependency for embedded Stacker.

## [0.5.0] - 2018-02-26
### Added
- Include `stacker-runway` script to allow embedded Stacker to be invoked directly.

## [0.4.2] - 2018-02-26
### Changed
- Declare explicit setuptools dependency on python < v3.

## [0.4.1] - 2018-02-23
### Changed
- Fix changed CFN parameters not being displayed during `runway plan`.

[Unreleased]: https://github.com/onicagroup/runway/compare/v1.7.2...HEAD
[1.7.2]: https://github.com/onicagroup/runway/compare/v1.7.1...v1.7.2
[1.7.1]: https://github.com/onicagroup/runway/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/onicagroup/runway/compare/v1.6.1...v1.7.0
[1.6.1]: https://github.com/onicagroup/runway/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/onicagroup/runway/compare/v1.5.2...v1.6.0
[1.5.2]: https://github.com/onicagroup/runway/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/onicagroup/runway/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/onicagroup/runway/compare/v1.4.4...v1.5.0
[1.4.4]: https://github.com/onicagroup/runway/compare/v1.4.3...v1.4.4
[1.4.3]: https://github.com/onicagroup/runway/compare/v1.4.2...v1.4.3
[1.4.2]: https://github.com/onicagroup/runway/compare/v1.4.1...v1.4.2
[1.4.1]: https://github.com/onicagroup/runway/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/onicagroup/runway/compare/v1.3.7...v1.4.0
[1.3.7]: https://github.com/onicagroup/runway/compare/v1.3.6...v1.3.7
[1.3.6]: https://github.com/onicagroup/runway/compare/v1.3.5...v1.3.6
[1.3.5]: https://github.com/onicagroup/runway/compare/v1.3.4...v1.3.5
[1.3.4]: https://github.com/onicagroup/runway/compare/v1.3.3...v1.3.4
[1.3.3]: https://github.com/onicagroup/runway/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/onicagroup/runway/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/onicagroup/runway/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/onicagroup/runway/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/onicagroup/runway/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/onicagroup/runway/compare/v1.0.3...v1.1.0
[1.0.3]: https://github.com/onicagroup/runway/compare/v1.0.1...v1.0.3
[1.0.1]: https://github.com/onicagroup/runway/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/onicagroup/runway/compare/v0.47.1...v1.0.0
[0.47.1]: https://github.com/onicagroup/runway/compare/v0.47.0...v0.47.1
[0.47.0]: https://github.com/onicagroup/runway/compare/v0.46.6...v0.47.0
[0.46.6]: https://github.com/onicagroup/runway/compare/v0.46.5...v0.46.6
[0.46.5]: https://github.com/onicagroup/runway/compare/v0.46.4...v0.46.5
[0.46.4]: https://github.com/onicagroup/runway/compare/v0.46.3...v0.46.4
[0.46.3]: https://github.com/onicagroup/runway/compare/v0.46.2...v0.46.3
[0.46.2]: https://github.com/onicagroup/runway/compare/v0.46.1...v0.46.2
[0.46.1]: https://github.com/onicagroup/runway/compare/v0.46.0...v0.46.1
[0.46.0]: https://github.com/onicagroup/runway/compare/v0.45.4...v0.46.0
[0.45.4]: https://github.com/onicagroup/runway/compare/v0.45.3...v0.45.4
[0.45.3]: https://github.com/onicagroup/runway/compare/v0.45.2...v0.45.3
[0.45.2]: https://github.com/onicagroup/runway/compare/v0.45.1...v0.45.2
[0.45.1]: https://github.com/onicagroup/runway/compare/v0.45.0...v0.45.1
[0.45.0]: https://github.com/onicagroup/runway/compare/v0.44.3...v0.45.0
[0.44.3]: https://github.com/onicagroup/runway/compare/v0.44.2...v0.44.3
[0.44.2]: https://github.com/onicagroup/runway/compare/v0.44.1...v0.44.2
[0.44.1]: https://github.com/onicagroup/runway/compare/v0.44.0...v0.44.1
[0.44.0]: https://github.com/onicagroup/runway/compare/v0.43.0...v0.44.0
[0.43.0]: https://github.com/onicagroup/runway/compare/v0.42.0...v0.43.0
[0.42.0]: https://github.com/onicagroup/runway/compare/v0.41.2...v0.42.0
[0.41.2]: https://github.com/onicagroup/runway/compare/v0.41.1...v0.41.2
[0.41.1]: https://github.com/onicagroup/runway/compare/v0.41.0...v0.41.1
[0.41.0]: https://github.com/onicagroup/runway/compare/v0.40.1...v0.41.0
[0.40.1]: https://github.com/onicagroup/runway/compare/v0.40.0...v0.40.1
[0.40.0]: https://github.com/onicagroup/runway/compare/v0.39.1...v0.40.0
[0.39.1]: https://github.com/onicagroup/runway/compare/v0.39.0...v0.39.1
[0.39.0]: https://github.com/onicagroup/runway/compare/v0.38.2...v0.39.0
[0.38.2]: https://github.com/onicagroup/runway/compare/v0.38.1...v0.38.2
[0.38.1]: https://github.com/onicagroup/runway/compare/v0.38.0...v0.38.1
[0.38.0]: https://github.com/onicagroup/runway/compare/v0.37.2...v0.38.0
[0.37.2]: https://github.com/onicagroup/runway/compare/v0.37.1...v0.37.2
[0.37.1]: https://github.com/onicagroup/runway/compare/v0.37.0...v0.37.1
[0.37.0]: https://github.com/onicagroup/runway/compare/v0.36.0...v0.37.0
[0.36.0]: https://github.com/onicagroup/runway/compare/v0.35.3...v0.36.0
[0.35.3]: https://github.com/onicagroup/runway/compare/v0.35.2...v0.35.3
[0.35.2]: https://github.com/onicagroup/runway/compare/v0.35.1...v0.35.2
[0.35.1]: https://github.com/onicagroup/runway/compare/v0.35.0...v0.35.1
[0.35.0]: https://github.com/onicagroup/runway/compare/v0.34.0...v0.35.0
[0.34.0]: https://github.com/onicagroup/runway/compare/v0.33.0...v0.34.0
[0.33.0]: https://github.com/onicagroup/runway/compare/v0.32.0...v0.33.0
[0.32.0]: https://github.com/onicagroup/runway/compare/v0.31.2...v0.32.0
[0.31.2]: https://github.com/onicagroup/runway/compare/v0.31.1...v0.31.2
[0.31.1]: https://github.com/onicagroup/runway/compare/v0.31.0...v0.31.1
[0.31.0]: https://github.com/onicagroup/runway/compare/v0.30.6...v0.31.0
[0.30.0]: https://github.com/onicagroup/runway/compare/v0.29.6...v0.30.0
[0.29.6]: https://github.com/onicagroup/runway/compare/v0.29.5...v0.29.6
[0.29.5]: https://github.com/onicagroup/runway/compare/v0.29.4...v0.29.5
[0.29.4]: https://github.com/onicagroup/runway/compare/v0.29.3...v0.29.4
[0.29.3]: https://github.com/onicagroup/runway/compare/v0.29.2...v0.29.3
[0.29.2]: https://github.com/onicagroup/runway/compare/v0.29.1...v0.29.2
[0.29.1]: https://github.com/onicagroup/runway/compare/v0.29.0...v0.29.1
[0.29.0]: https://github.com/onicagroup/runway/compare/v0.28.0...v0.29.0
[0.28.0]: https://github.com/onicagroup/runway/compare/v0.27.1...v0.28.0
[0.27.1]: https://github.com/onicagroup/runway/compare/v0.27.0...v0.27.1
[0.27.0]: https://github.com/onicagroup/runway/compare/v0.26.0...v0.27.0
[0.26.0]: https://github.com/onicagroup/runway/compare/v0.25.0...v0.26.0
[0.25.0]: https://github.com/onicagroup/runway/compare/v0.24.0...v0.25.0
[0.24.0]: https://github.com/onicagroup/runway/compare/v0.23.3...v0.24.0
[0.23.3]: https://github.com/onicagroup/runway/compare/v0.23.2...v0.23.3
[0.23.2]: https://github.com/onicagroup/runway/compare/v0.23.1...v0.23.2
[0.23.1]: https://github.com/onicagroup/runway/compare/v0.23.0...v0.23.1
[0.23.0]: https://github.com/onicagroup/runway/compare/v0.22.3...v0.23.0
[0.22.3]: https://github.com/onicagroup/runway/compare/v0.22.2...v0.22.3
[0.22.2]: https://github.com/onicagroup/runway/compare/v0.22.1...v0.22.2
[0.22.1]: https://github.com/onicagroup/runway/compare/v0.22.0...v0.22.1
[0.22.0]: https://github.com/onicagroup/runway/compare/v0.21.0...v0.22.0
[0.21.0]: https://github.com/onicagroup/runway/compare/v0.20.7...v0.21.0
[0.20.7]: https://github.com/onicagroup/runway/compare/v0.20.5...v0.20.7
[0.20.5]: https://github.com/onicagroup/runway/compare/v0.20.4...v0.20.5
[0.20.4]: https://github.com/onicagroup/runway/compare/v0.20.3...v0.20.4
[0.20.3]: https://github.com/onicagroup/runway/compare/v0.20.1...v0.20.3
[0.20.1]: https://github.com/onicagroup/runway/compare/v0.20.0...v0.20.1
[0.20.0]: https://github.com/onicagroup/runway/compare/v0.19.0...v0.20.0
[0.19.0]: https://github.com/onicagroup/runway/compare/v0.18.0...v0.19.0
[0.18.0]: https://github.com/onicagroup/runway/compare/v0.17.0...v0.18.0
[0.17.0]: https://github.com/onicagroup/runway/compare/v0.16.0...v0.17.0
[0.16.0]: https://github.com/onicagroup/runway/compare/v0.15.3...v0.16.0
[0.15.3]: https://github.com/onicagroup/runway/compare/v0.15.2...v0.15.3
[0.15.2]: https://github.com/onicagroup/runway/compare/v0.15.1...v0.15.2
[0.15.1]: https://github.com/onicagroup/runway/compare/v0.15.0...v0.15.1
[0.15.0]: https://github.com/onicagroup/runway/compare/v0.14.3...v0.15.0
[0.14.3]: https://github.com/onicagroup/runway/compare/v0.14.2...v0.14.3
[0.14.2]: https://github.com/onicagroup/runway/compare/v0.14.1...v0.14.2
[0.14.1]: https://github.com/onicagroup/runway/compare/v0.14.0...v0.14.1
[0.14.0]: https://github.com/onicagroup/runway/compare/v0.13.0...v0.14.0
[0.13.0]: https://github.com/onicagroup/runway/compare/v0.12.3...v0.13.0
[0.12.3]: https://github.com/onicagroup/runway/compare/v0.12.2...v0.12.3
[0.12.2]: https://github.com/onicagroup/runway/compare/v0.12.1...v0.12.2
[0.12.1]: https://github.com/onicagroup/runway/compare/v0.12.0...v0.12.1
[0.12.0]: https://github.com/onicagroup/runway/compare/v0.11.1...v0.12.0
[0.11.1]: https://github.com/onicagroup/runway/compare/v0.11.0...v0.11.1
[0.11.0]: https://github.com/onicagroup/runway/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/onicagroup/runway/compare/v0.9.1...v0.10.0
[0.9.1]: https://github.com/onicagroup/runway/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/onicagroup/runway/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/onicagroup/runway/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/onicagroup/runway/compare/v0.6.2...v0.7.0
[0.6.2]: https://github.com/onicagroup/runway/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/onicagroup/runway/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/onicagroup/runway/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/onicagroup/runway/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/onicagroup/runway/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/onicagroup/runway/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/onicagroup/runway/compare/v0.4.0...v0.4.1
