/**
 * Reporting functionality for test runs
 */
import colors from 'colors';

interface ReportEntry {
    title: string;
    result: boolean;
}

interface ReportSection {
    title: string;
    tests: ReportEntry[];
}

export default class Reporter {
    /** The array of report objects */
    report:ReportSection[];

    /**
     * Constructor
     */
    constructor() { this.report = []; }

    /**
     * Given a title add a section with an empty tests array to the stack
     *
     * @param title
     */
    addSection(title:string) {
        this.report.push({
            title,
            tests: []
        } as ReportSection);
        return this.report;
    }

    /**
     * Add a test result to the test section array
     *
     * @param index
     * @param title
     * @param result
     */
    addTestResult(index:number, title: string, result: boolean) {
        if(this.report[index]) {
            this.report[index].tests.push({ title, result } as ReportEntry);
        }
        return this.report;
    }

    /**
     * Return a CLI formatted report of the test findings
     */
    formatReport(): void {
        console.log(colors.yellow('~~~~~~~~~~~~~[ E2E Test Report ]~~~~~~~~~~~~~'));
        this.report.forEach(section => {
            console.log(colors.cyan(`${section.title}:`));
            if(section.tests.length === 0) {
                console.log(colors.yellow('\t- No Tests Results Were Reported'));
            } else {
                section.tests.forEach(test => {
                    const value = test.result ? colors.green('PASSED') : colors.red('FAILED');
                    console.log(`\t- ${test.title}: ${value}`);
                });
            }
        });
    }
}
