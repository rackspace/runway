import HomePage from '../pages/home-page';
import Test from '../../test'

export default class DistributionDisabledTests extends Test {
    /** The HomePage element */
    homePage:HomePage;

    /**
     * Setup our testing fixtures
     */
    async setup(): Promise<void> {
        this._spinUp('src/static-site/run/distribution-disabled', async () => {
            const main = await this.getStack('dev-static-site-e2e');
            const domainOutput = this.getOutput(main, 'BucketWebsiteURL');
            this.homePage = new HomePage(this._driver, domainOutput!.OutputValue!);
        });
    }

    /**
     * Teardown any fixtures
     */
    async teardown(): Promise<void> {
        this._spinDown('src/static-site/run/distribution-disabled', async () => {})
    }

    /**
     * Run all of our specific tests for this module
     */
    async tests(): Promise<void> {
        await this.test_for_page_load();
    }

    /**
     * Test that the page has properly loaded
     */
    async test_for_page_load(): Promise<void> {
        await this.homePage.gotoBaseUrl();
        await this.homePage.getMainDivText().then(async (text) => {
            await this.assert(
                'test_for_page_load',
                text === 'Successful e2e Test'
            )
        })
    }
}
