/**
 * Static Site HomePage element
 */
import {By, WebElement} from 'selenium-webdriver';
import Page from '../../page';

export default class HomePage extends Page {
    /** The main container of the page */
    main = By.id('main');

    /**
     * Retrieve the main div of the page
     */
    async getMainDiv(): Promise<WebElement> {
        return await this.findElement(this.main)
    }

    /**
     * Get the text from the main div of the page
     */
    async getMainDivText(): Promise<string> {
        return await (await this.getMainDiv()).getText();
    }
}
