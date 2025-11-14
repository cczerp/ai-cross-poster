from pydantic import BaseModel
from typing import List, Optional

class ListingData(BaseModel):
    title: str
    description: str
    price: float
    condition: str
    category: Optional[str] = None
    brand: Optional[str] = None
    quantity: Optional[int] = 1
    shipping_weight: Optional[str] = None
    images: List[str] = []
