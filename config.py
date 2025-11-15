import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MERCARI_EMAIL = os.getenv("MERCARI_EMAIL")
    MERCARI_PASSWORD = os.getenv("MERCARI_PASSWORD")

    POSH_EMAIL = os.getenv("POSH_EMAIL")
    POSH_PASSWORD = os.getenv("POSH_PASSWORD")

    FACEBOOK_EMAIL = os.getenv("FB_EMAIL")
    FACEBOOK_PASSWORD = os.getenv("FB_PASSWORD")

    EBAY_EMAIL = os.getenv("EBAY_EMAIL")
    EBAY_PASSWORD = os.getenv("EBAY_PASSWORD")
