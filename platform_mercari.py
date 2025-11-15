from platforms.base_platform import BasePlatform
from config import Config
from utils.logger import log
from listing_data import ListingData

class Mercari(BasePlatform):

    async def login(self):
        log("Logging into Mercari...")
        self.page.goto("https://www.mercari.com/login/")
        await self.page.fill('input[name="email"]', Config.MERCARI_EMAIL)
        await self.page.fill('input[name="password"]', Config.MERCARI_PASSWORD)
        await self.page.click('button[type="submit"]')
        await self.page.wait_for_load_state("networkidle")
        log("Mercari login successful.")

    async def create_listing(self, data: ListingData):
        log("Starting Mercari listing...")

        self.page.goto("https://www.mercari.com/sell/")
        await self.page.wait_for_load_state("networkidle")

        # Upload images
        for img in data.images:
            await self.page.set_input_files('input[type="file"]', img)

        # Fill main fields
        await self.page.fill('input[name="title"]', data.title)
        await self.page.fill('textarea[name="description"]', data.description)
        await self.page.fill('input[name="price"]', str(data.price))

        # Condition dropdown
        await self.page.click('[data-testid="condition-selector"]')
        await self.page.click(f'text="{data.condition}"')

        # Submit listing
        await self.page.click('button:has-text("List")')
        await self.page.wait_for_timeout(2000)

        log("Mercari listing created successfully.")
