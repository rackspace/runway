# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/onicagroup/runway/compare/v0.11.0...HEAD
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
