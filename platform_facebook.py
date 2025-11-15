from platforms.base_platform import BasePlatform
from listing_data import ListingData
from config import Config
from utils.logger import log

class Facebook(BasePlatform):

    async def login(self):
        log("Logging into Facebook...")
        self.page.goto("https://www.facebook.com/login")
        await self.page.fill("#email", Config.FACEBOOK_EMAIL)
        await self.page.fill("#pass", Config.FACEBOOK_PASSWORD)
        await self.page.click("button[name=login]")
        await self.page.wait_for_load_state("networkidle")
        log("Facebook login OK.")

    async def create_listing(self, data: ListingData):
        log("Creating Facebook listing...")
        self.page.goto("https://www.facebook.com/marketplace/create/item")

        await self.page.set_input_files('input[type="file"]', data.images)
        await self.page.fill('input[aria-label="Title"]', data.title)
        await self.page.fill('input[aria-label="Price"]', str(data.price))
        await self.page.fill('textarea', data.description)

        await self.page.click('text="Next"')
        await self.page.click('text="Publish"')

        log("Facebook listing posted.")
