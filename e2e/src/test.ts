/**
 * Base class for an E2E test. Provides shared functionality
 */
import AWS from 'aws-sdk';
import { Builder } from 'selenium-webdriver';
import { exec } from 'child_process';
import { strict as assert } from 'assert';
import { WebDriver } from 'selenium-webdriver';
import Runner from './runner';

export default class Test {
    /** The selenium WebDriver */
    _driver:WebDriver;
    /** The cloudformation client resource */
    cloudformation = new AWS.CloudFormation();
    /** The test runner */
    runner:Runner;
    /** Whether we encountered an error during the test */
    error = false;

    /**
     * Constructor
     *
     * @param runner The test runner
     */
    constructor(runner:Runner) {
      this.runner = runner;
      this.setup();
    }

    /**
     * Placeholder function for test setup
     *
     * @throws Error
     */
    async setup(): Promise<void> {
      throw new Error('The setup() function must be populated on your child class');
    }

    /**
     * Placeholder function for teardown
     *
     * @throws Error
     */
    async teardown(): Promise<void> {
      throw new Error('The teardown() function must be populated on your child class');
    }

    /**
     * Placeholder function for e2e tests
     *
     * @throws Error
     */
    async tests(): Promise<void> {
      throw new Error('The tests() function must be populated on your child class');
    }

    /**
     * Run the tests and issue teardown upon completion
     */
    async run(): Promise<void> {
      try {
        await this.tests();
      } catch(err) {
        this.error = true;
      } finally {
        await this.teardown();
      }
    }

    /**
     * Assert a given test. Ensure we are meeting e2e criteria
     *
     * @param testName The name of the test being ran
     * @param assertion The assertion conditional
     */
    async assert(testName:string, assertion:boolean) {
        try {
            assert(assertion);
        } catch(err) {
            if(err.name === 'AssertionError [ERR_ASSERTION]') {
                this.runner.report(testName, false);
                return false;
            }
            this.runner.report(`${testName} [SYSTEM_ERROR]`, false);
            return false;
        }
        this.runner.report(testName, true);
        return true;
    }

    /**
     * SpinUp/Deploy the given runway stack at path. Execute any functionality
     * Upon exit
     *
     * @param path
     * @param executeFunction
     */
    async _spinUp(path:string, executeFunction:()=>any): Promise<void> {
      process.env.CI = '1';
      process.env.DEPLOY_ENVIRONMENT = 'dev';
      const runway = exec(
        `cd ${path} && pipenv sync && pipenv install && pipenv run runway deploy`
      );
      runway.stdout?.on('data', (data) => console.log(data));
      runway.stderr?.on('data', (data) => console.log(data));
      runway.on('exit', async() => {
        this._driver = await new Builder().forBrowser('chrome').build();
        this.runner.reporter.addSection(`${this.constructor.name}`);
        executeFunction().then(() => { this.run(); });
      });
    }

    /**
     * SpinDown/Destroy the given runway stack at path. Run any functionality upon exit.
     *
     * @param path
     * @param executeFunction
     */
    async _spinDown(path:string, executeFunction:()=>any): Promise<void> {
      process.env.CI = '1';
      process.env.DEPLOY_ENVIRONMENT = 'dev';
      const runway = exec(`cd ${path} && pipenv run runway destroy`);
      runway.stdout?.on('data', (data) => console.log(data));
      runway.stderr?.on('data', (data) => console.log(data));
      runway.on('exit', async() => {
        await this._driver.quit();
        await executeFunction().then(() => {
          if(this.error) {
            // If we received an error try running the test again. May be
            // just a temporary issue
            this.runner.increaseErrorCount();
            this.runner.runAgain();
          } else {
            this.runner.runNext();
          }
        });
      });
    }

    /**
     * Given a stackName retrieve the stack information from AWS
     *
     * @param stackName
     */
    async getStack(stackName:string): Promise<AWS.CloudFormation.Stack> {
      const stacks = await this.cloudformation.describeStacks({ StackName: stackName }).promise();
      return Promise.resolve(stacks.Stacks![0]);
    }

    /**
     * From a given stack retrieve a specific OutputValue based on the name key
     *
     * @param stack
     * @param outputName
     */
    getOutput(stack:AWS.CloudFormation.Stack, outputName:string): AWS.CloudFormation.Output|undefined {
        return stack.Outputs?.find((output:AWS.CloudFormation.Output) => {
            return output.OutputKey == outputName
        });
    }
}
