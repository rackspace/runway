/**
 * Primary index file for test runs.
 * Import your test and add to the Runner signature call from here.
 */
import Runner from './src/runner';
import StaticSiteTests from './src/static-site/tests/static-site';
import DistributionDisabledTests from './src/static-site/tests/distribution-disabled';

const runner = new Runner([
    StaticSiteTests,
    DistributionDisabledTests
]);

runner.run();

// If an interupt is thrown show the current formatted report
process.on('SIGINT', () => {
    runner.reporter.formatReport();
    process.exit();
});
