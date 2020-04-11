/**
 * A Page element.
 * Contains functionality for interacting with a specific page during an E2E test
 */
import { By, WebDriver, WebElement } from 'selenium-webdriver';

export default class Page {
    /** The baseUrl for the specific page */
    baseUrl:string;
    /**
     * The Selenium WebDriver
     *
     * @private
     */
    _driver:WebDriver;

    /**
     * Constructor
     *
     * @param driver
     * @param baseUrl
     */
    constructor(driver:WebDriver, baseUrl:string) {
        this.baseUrl = baseUrl;
        this._driver = driver;
    }

    /**
     * GoTo the baseUrl for the given page
     */
    async gotoBaseUrl(): Promise<void> {
        await this._driver.get(this.baseUrl);
    }

    /**
     * GoTo a specific url relative to the baseUrl
     *
     * @param url
     */
    async goto(url:string): Promise<void> {
        await this._driver.get(this.baseUrl + url);
    }

    /**
     * Find an element on the page
     *
     * @param locator
     */
    async findElement(locator:By): Promise<WebElement> {
        return await this._driver.findElement(locator);
    }
}
