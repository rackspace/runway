## Running Tests
From the `integration_tests` folder run `make test`.

This will iterate through all the folders that start with `test_` and look for `*.py` files
that also start with `test_` and execute the `init()`, `run()`, and `teardown()` methods in each
test.


## Creating Tests
1. Create a new folder that starts with `test_` and place it in the `integration_tests` folder.
2. Create a new python file that starts with `test_` and place it in the root of your new folder.
3. Create a class in the python file that inherits from `IntegrationTest` located in the root of this folder in `integration_test.py`.
4. Create 3 methods `init()`, `run()`, and `teardown()` that take the `self` parameter.

**NOTE:** For a test to run properly, it **MUST** inherit from the `IntegrationTest` class located in `integration_test.py`.


## Helper Functions
In `util.py` there are a couple of helper functions:
* `import_tests`
    * This will import tests from a given path and pattern, so your tests can import more tests.
    * See `test_terraform.py` for an example of this.
* `execute_tests`
    * Given a list of classes, it will iterate through them and run `init()`, `run()`, and `teardown()`.
    * This will also give a report of the results of each test.
