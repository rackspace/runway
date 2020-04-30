# infrastructure

Infrastructure as code that is used in the testing and deployment of Runway.

## Usage

This directory uses a **Makefile** to orchestrate runway actions across multiple AWS accounts that are not connected with assumable roles.

To execute Runway for an AWS account, use the following command syntax.

```shell
$ make <runway-subcommand> <aws-account>
```

### Example

```shell
$ make deploy testing
$ make test public
```
