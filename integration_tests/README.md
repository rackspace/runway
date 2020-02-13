# Integration Tests


## Infrastructure

When adding new top-level tests, infrastructure must be redeployed from [integration_test_infrastructure](../integration_test_infrastructure).

Each top-level test is run within its own CodeBuild project.


## Running Tests

From the `integration_tests` folder run `make test`.

This will iterate through all the folders that start with `test_` and look for `*.py` files
that also start with `test_` and execute the `run()` and `teardown()` methods in each test.


## Creating Tests

**IMPORTANT: Read the Caveats section below BEFORE trying a write integration tests.**

1. Create a new folder that starts with `test_` and place it in the `integration_tests` folder. The folder name after the prefix must contain **lowercase alphanumeric characters only**.
2. Create a new python file that starts with `test_` and place it in the root of your new folder. The file must be named the same as the folder in **step 1**.
3. Create a class in the python file that inherits from `IntegrationTest` located in the root of this folder in `integration_test.py`. The class name must be the same as the folder/filename suffix but, can have any number of capital letters.
4. Create 2 methods `run()` and `teardown()` that take the `self` parameter.
    - `run()` should contain the logic to setup the test and the assertions
    - `teardown()` should contain the logic to cleanup after all the tests have completed. (e.g. `runway destroy` and `send2trash()`)

### Caveats

- Any infrastructure created by a test must have stack names and resources names unique to that test to avoid collisions since tests will be run concurrently.
- All import must be absolute with `integration_tests` as the base. This is due to the mechanics used to import the tests.
- For a top-level test to run properly, it **MUST** inherit from the `IntegrationTest` class located in `integration_test.py`.
- If using pipenv within a test (CDK for python does this) you must delete the venv created during `runway deploy` BEFORE using `runway destroy` in `teardown()`. Since its being run in a nested copy of pipenv, it will result in a prompt when using `pipenv sync -d --three` if there is an existing venv.


## Helper Functions

In `util.py` there are a couple of helper functions:
- `import_tests`
  - This will import tests from a given path and pattern, so your tests can import more tests.
  - See `test_terraform.py` for an example of this.
- `execute_tests`
  - Given a list of classes, it will iterate through them and run  `run()` and `teardown()`.
  - This will also give a report of the results of each test.

## Permissions
Put a file called policies.yaml in the integration test folder in order to define permissions. e.g. /integration_tests/test_cdk/policies.yaml

Whenever permissions are updated, the permissions stack must be redeployed with the following command from the folder '/integration_test_infrastructure/codebuild/common': pipenv run runway deploy

