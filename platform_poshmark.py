from platforms.base_platform import BasePlatform
from listing_data import ListingData
from config import Config
from utils.logger import log

class Poshmark(BasePlatform):

    async def login(self):
        log("Logging into Poshmark...")
        self.page.goto("https://poshmark.com/login")
        await self.page.fill("#email", Config.POSH_EMAIL)
        await self.page.fill("#password", Config.POSH_PASSWORD)
        await self.page.click("button[type=submit]")
        await self.page.wait_for_load_state("networkidle")
        log("Poshmark login successful.")

    async def create_listing(self, data: ListingData):
        log("Creating Poshmark listing...")
        self.page.goto("https://poshmark.com/create-listing")

        await self.page.set_input_files("input[type=file]", data.images)

        await self.page.fill('input[name="title"]', data.title)
        await self.page.fill('textarea[name="description"]', data.description)
        await self.page.fill('input[name="price"]', str(data.price))

        await self.page.click("button:has-text('List Item')")
        log("Poshmark listing posted.")
