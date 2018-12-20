# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Improve approval resilency on CFN stack updates (Stacker #674)

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
- Update embedded stacker to fix interative CFN stack updates with empty string parameters

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
    * These can be used to make Terraform, Serverless, and CloudFormation (Stacker) variable/environment files optional.

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
    * This fixes duplicate code checking and should greatly speed up tests

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
    * They provide their own error messages/stacktrace; runway errors just obfuscate them
- Fix 0.20.1 regression of global stacker install use (instead of embedded version)

## [0.20.3] - 2018-06-13
### Fixed
- Fix stacker invocation error introduced in v0.20.1

## [0.20.1] - 2018-06-13
### Fixed
- Multiple CFN modules can now use the same remote Stacker package at different versions
    * Previously, the first module to load a remote package (e.g. stacker_blueprints at tag v1.0.3) would have that tagged version stuck for the rest of the runway deployment. Now, subsequent modules can specify other tags/commits/etc of the same remote package.

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
    * This should provide a better experience for user IDEs when editing stacker blueprints

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
    * Any previous `backend.tfvars` values should be moved into the primary (e.g. main.tf) backend config
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
    * This is necessary for the upcoming `destroy`/`dismantle` (e.g. `sls remove`) support
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

[Unreleased]: https://github.com/onicagroup/runway/compare/v0.38.1...HEAD
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
