# Tests

Runway's tests are split into three catagories; [functional](#functional-tests), [integration](#integration-tests), and [unit](#unit-tests).

- [Tests](#tests)
  - [Test Types](#test-types)
    - [Functional Tests](#functional-tests)
    - [Integration Tests](#integration-tests)
    - [Unit Tests](#unit-tests)
  - [Running Tests](#running-tests)

## Test Types

### Functional Tests

Test the end-to-end functionally of Runway.

- High level tests that invoke Runway using either API or CLI.
- There should be fewer of these tests then in any other category.
- There are to be **NO MOCKS/PATCHES** in these tests.
- Each subdirectory is a fully contained test.

### Integration Tests

Test the interactions between Runway's components and some external components.

- There should be fewer of these tests then unit tests.
- Mocking/patching some things are fine if its needed for inspection but, it should be limited.

### Unit Tests

The the operation of each function/method individually.

- Low level tests that import individual functions and classes to invoke them directly.
- Mocks should be used to isolate each function/method.


## Running Tests

Tests can be run using `make` commands from the root of the repo.

|         Command         |       Description        |
|-------------------------|--------------------------|
| `make test`             | integration & unit tests |
| `make test-functional`  | functional tests         |
| `make test-integration` | integration tests        |
| `make test-unit`        | unit tests               |
