from platforms.base_platform import BasePlatform
from listing_data import ListingData
from config import Config
from utils.logger import log

class Ebay(BasePlatform):

    async def login(self):
        log("Logging into eBay...")
        self.page.goto("https://signin.ebay.com/")
        await self.page.fill("#userid", Config.EBAY_EMAIL)
        await self.page.click("#signin-continue-btn")
        await self.page.fill("#pass", Config.EBAY_PASSWORD)
        await self.page.click("#sgnBt")
        await self.page.wait_for_load_state("networkidle")
        log("eBay login OK.")

    async def create_listing(self, data: ListingData):
        log("Creating eBay listing...")
        self.page.goto("https://www.ebay.com/sl/sell")

        await self.page.set_input_files('input[type=file]', data.images)
        await self.page.fill('input[name="title"]', data.title)
        await self.page.fill('textarea[name="description"]', data.description)
        await self.page.fill('input[name="binPrice"]', str(data.price))

        await self.page.click('button:has-text("List item")')
        log("eBay listing posted.")
