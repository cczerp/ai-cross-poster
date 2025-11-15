from listing_data import ListingData

class BasePlatform:
    def __init__(self, page):
        self.page = page

    def login(self):
        raise NotImplementedError

    def create_listing(self, data: ListingData):
        raise NotImplementedError
