/**
 * Automation for running tests in sequence
 */
import Reporter from './reporter';

export default class Runner {
    /** Maximum number of errors before the loop quits */
    MAX_ERROR_COUNT = 10;
    /** The current test index */
    index = -1;
    /** Current error count */
    errorCount = 0;
    /** The tests to be ran, supplied with classes */
    tests:Array<any>;
    /** The reporter object to inform of test conclusion */
    reporter = new Reporter();

    /**
     * Constructor
     *
     * @param testClasses
     */
    constructor(testClasses:Array<any>) {
        this.tests = testClasses;
    }

    /**
     * Run the current test based on the index.
     * When we run out of tests then display the report.
     */
    run(): void {
        this.index++;
        const currentIndex = this.index - this.errorCount;
        if(this.tests[currentIndex] && this.errorCount !== this.MAX_ERROR_COUNT) {
            new this.tests[currentIndex](this);
        } else {
            this.reporter.formatReport();
        }
    }

    /** Alias for run() */
    runNext(): void { this.run(); }

    /** Alias for run() */
    runAgain(): void { this.run(); }

    /** Increase the current error count */
    increaseErrorCount(): number {
        return this.errorCount++;
    }

    /**
     * Report a test result to the reporter.
     *
     * @param title
     * @param result
     */
    report(title:string, result:boolean) {
        this.reporter.addTestResult(this.index, title, result);
        return this.reporter.report;
    }
}
