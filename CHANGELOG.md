# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Fixed
- Bypass CFN blueprint file execution mode check on Windows.

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

[Unreleased]: https://github.com/onicagroup/runway/compare/v0.17.0...HEAD
[0.16.0]: https://github.com/onicagroup/runway/compare/v0.16.0...v0.17.0
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
[0.10.0]: https://github.com/onicagroup/runway/compare/v0.9.0...v0.10.0
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
