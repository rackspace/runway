import HomePage from '../pages/home-page';
import Test from '../../test'

export default class StaticSiteTests extends Test {
    /** The Home Page element */
    homePage:HomePage;

    /**
     * Setup our tests
     */
    async setup(): Promise<void> {
        this._spinUp('src/static-site/run/static-site', async () => {
            const main = await this.getStack('dev-static-site-e2e');
            const distributionOutput = this.getOutput(main, 'CFDistributionDomainName');
            const domain = 'https://' + distributionOutput!.OutputValue;
            this.homePage = new HomePage(this._driver, domain);
        });
    }

    /**
     * Tear down our tests
     */
    async teardown(): Promise<void> {
        this._spinDown('src/static-site/run/static-site', async () => {});
    }

    /**
     * Add tests to run list
     */
    async tests(): Promise<void> {
        await this.test_for_page_load();
    }

    /**
     * Verify page loaded successfully
     */
    async test_for_page_load(): Promise<void> {
        await this.homePage.gotoBaseUrl();
        await this.homePage.getMainDivText().then(async (text) => {
            await this.assert(
                'test_for_page_load',
                text === 'Successful e2e Test',
            )
        })
    }
}
