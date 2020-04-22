# infrastructure

Infrastructure as code that is used in the testing and deployment of Runway.

## Usage

This directory uses a **Makefile** to orchestrate runway actions across multiple environments.

To execute Runway for an environment, use the following command syntax.

```shell
$ make <runway-subcommand> <environment>
```

### Example

```shell
$ make deploy integration-tests
$ make test public
```
