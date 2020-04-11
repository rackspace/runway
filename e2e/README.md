Runway End-to-End (e2e) Testing
===============================

Overview
--------

The Runway e2e suite is written in Typescript/node and provides a simple framework for writing e2e tests for the application. Under the hood [Selenium](https://www.selenium.dev/) is being used for browser automation with a Chromedriver browser. The following sections briefly go over basic concepts of the framework.

Usage
-----

From the Runway root folder
`cd e2e && make test`

Tests
-----

Tests are the primary file type for the structure. They should extend off of `Test` in the `src/test.ts` file. Each test is required to contain three specific functions:

`setup()`: The location where all fixtures for your test should be created and implemented. A `_spinUp` protected function is provided that will allow you to easily point at a specific directory and launch your Runway configuration. Example:

```typescript
    async setup(): Promise<void> {
        this._spinUp('src/my_tests/run/test_scenario_1', async () => {
            const main = await this.getStack('dev-my-runway-stack');
            const domain = this.getOutput(main, 'MyUrl').OutputValue;
            this.homePage = new HomePage(this._driver, domain);
        })
    }
```

`teardown()`: Any teardown activity that should happen before the destruction of the stack. A `_spinDown` protected function is provided that will allow you to easily point at a specific directory and destroy your Runway configuration. Example:

```typescript
    async teardown(): Promise<void> {
        this._spinDown('src/my_tests/run/test_scenario_1', async () => {
            const main = await this.getStack('dev-my-runway-stack');
            const userPoolId = this.getOutput(main, 'MyCognitoUserPoolId').OutputValue;
            const params = { UserPoolId: userPoolId, Username: 'foo' }
            const promise = await cognito.adminDeleteUser(params).promise();
        })
    }
```

`tests()`: A listing of all the individual tests (located in the file) that you would like ran. These tests can be constructed to your choosing. Below is an example of the `tests()` method with a corresponding individual test:

```typescript
    async tests(): Promise<void> {
        await this.test_for_page_load();
    }

    async test_for_page_load(): Promise<void> {
        await this.homePage.gotoBaseUrl();
        await this.homePage.getMainDivText().then(async (text) => {
            await this.assert(
                'Test for Page Load",
                text === 'Welcome to my homepage"
            )
        })
    }
```

Pages
-----

Pages (which inherit from `src/page`) are used to house information specific to a page you will be testing against. The idea being that each individual page separates the concern of their structrual testing.

Individual pages will vary, and their functionality in turn will be dependent on their needs. However, it is generally expected that targetted page elements should be constructed as class parameters utilizing Selenium's `By` methodology, and then individual testing scenarios (example: Getting test from a `div`) will be represented as individual methods of the page. Example:

```typescript
    import {By} from 'selenium-webdriver';
    import Page from '../../page';

    export default class HomePage extends Page {
        main = By.id('main');

        async getMainDivText(): Promise<string> {
            return await(await this.findElement(this.main)).getText()
        }
    }
```

Run directory
-------------

The `run` directory is where your `runway.yaml` as well as any corresponding fixture files should be placed. This will be the directory you call to during `_spinUp` and `_spinDown` calls.
