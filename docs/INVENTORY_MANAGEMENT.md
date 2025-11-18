# Inventory Management System

## Overview

The AI Cross-Poster now includes a comprehensive inventory management system designed to help resellers track their items and find them quickly when they sell.

## Key Features

### 1. **Storage Location Tracking** 📍

Assign physical storage locations to your items (e.g., "B1", "C2", "Shelf-3") so you can find them instantly when they sell.

**How it works:**
- When creating a listing, enter the storage location in the "Storage Location" field
- Common formats: B1, C2, Shelf-3, Box-A, Bin-12, etc.
- When the item sells, the location is shown prominently in the notification

**Example Workflow:**
```
1. Take photos of blue Nike shirt
2. AI generates listing
3. Enter "B1" in Storage Location field
4. Put shirt in Bin 1 with other items
5. Shirt sells on eBay → Notification shows "Location: B1"
6. Go to Bin 1, find shirt, ship it!
```

### 2. **Dual Inventory Modes**

#### Mode A: 1-to-1 Single Items (Default)
Perfect for individual resellers with unique items.

- Each listing = 1 item (quantity = 1)
- When sold:
  - ✅ Immediately marks as "sold" in database
  - ⏰ **15-minute cooldown** before canceling on other platforms
  - 📍 Shows storage location to help you find the item
  - ✅ After 15 minutes, automatically cancels on other platforms

**Why 15 minutes?**
- Gives you time to locate the item in storage
- Verify it's actually there and matches the listing
- Check condition before shipping
- Cancel the sale if there's an issue

#### Mode B: Multi-Quantity
For sellers with multiple units of the same item.

- Set quantity > 1 when creating listing
- When sold:
  - ✅ Reduces quantity by 1
  - ✅ Updates quantity on all platforms
  - ✅ Only cancels when quantity reaches 0

### 3. **Automatic Cross-Platform Sync**

- Lists on multiple platforms simultaneously (eBay, Mercari, etc.)
- When item sells on one platform:
  - Immediately marks as sold in database
  - Schedules cancellation on other platforms (15-min delay)
  - Prevents overselling across platforms

### 4. **Enhanced Sale Notifications**

When an item sells, you'll see:
```
🎉 SALE NOTIFICATION
=====================
Item: Blue Nike Shirt Size M
Platform: eBay
Sale Price: $25.00

📍 STORAGE LOCATION: B1
   Go to B1 to find and ship this item!

Cost: $5.00
Profit: $20.00 (80.0%)
=====================
```

## Using the GUI

### Creating a Listing

1. **Add Photos** → Click "Add Photos" button
2. **AI Analysis** → Click "Analyze with AI" to auto-fill details
3. **Set Inventory Details:**
   - **Storage Location:** Enter where you put the item (B1, C2, etc.)
   - **Quantity:** Enter 1 for single items, >1 for multiples
4. **Save or Post:**
   - Click "Save as Draft" to save for later
   - Click "Post Now" to list immediately

### When an Item Sells

The system automatically:
1. Shows storage location in console and notification
2. Marks listing as sold
3. Waits 15 minutes (cooldown period)
4. Cancels on other platforms after cooldown

## Background Scheduler

To process scheduled cancellations, run the background scheduler:

```bash
# Run manually
python -m src.sync.cancellation_scheduler

# Or add to crontab (runs every minute)
* * * * * cd /home/user/ai-cross-poster && python -m src.sync.cancellation_scheduler
```

The scheduler checks every 60 seconds for pending cancellations and processes them automatically.

## Database Fields

### Listings Table (New Fields)
- `quantity` (INTEGER) - Number of items available (default: 1)
- `storage_location` (TEXT) - Physical location code (e.g., "B1")

### Platform Listings Table (New Fields)
- `cancel_scheduled_at` (TIMESTAMP) - When to auto-cancel after sale
- `status` can now be: `pending`, `active`, `sold`, `failed`, `canceled`, `pending_cancel`

## API Changes

### Creating Listings
```python
from src.schema import UnifiedListing, Price, Photo

listing = UnifiedListing(
    title="Blue Nike Shirt Size M",
    price=Price(amount=25.00),
    photos=[Photo(local_path="./photo1.jpg", is_primary=True)],
    quantity=1,  # NEW: Quantity
    location="B1",  # NEW: Storage location
    # ... other fields
)
```

### Marking as Sold
```python
from src.sync import MultiPlatformSyncManager

manager = MultiPlatformSyncManager.from_env()

# Mark as sold (with 15-minute cooldown)
result = manager.mark_sold(
    listing_id=123,
    sold_platform="ebay",
    sold_price=25.00,
    quantity_sold=1,  # NEW: How many sold
)

print(result['storage_location'])  # Shows "B1"
print(result['remaining_quantity'])  # Shows 0
```

## Migration

Existing databases will be automatically migrated when you first run the app. The migration adds:
- `quantity` column to `listings` table (default: 1)
- `storage_location` column to `listings` table
- `cancel_scheduled_at` column to `platform_listings` table

No data loss - all existing listings will have quantity set to 1.

## Best Practices

### For 1-to-1 Sellers (Individual Items)

1. **Organize with bins/totes:**
   - Label bins: A, B, C, D, etc.
   - Number positions: 1, 2, 3, 4, etc.
   - Storage codes: B1, B2, C1, C2, etc.

2. **Workflow:**
   - Photo → AI Analysis → Enter storage location → Put item in that location
   - When sold → Check notification for location → Find item → Ship

3. **Use the 15-minute cooldown:**
   - Find the item in storage
   - Verify condition matches listing
   - If issue found, cancel the sale before cooldown ends

### For Multi-Quantity Sellers

1. **Set quantity when creating listing**
2. **Store all units together** (same location code)
3. **System auto-updates quantity** on platforms when one sells
4. **Only cancels when** quantity reaches 0

## Troubleshooting

### Cancellation not happening after 15 minutes
- Make sure the background scheduler is running:
  ```bash
  python -m src.sync.cancellation_scheduler
  ```

### Can't find storage location field in GUI
- Update to latest version
- Field is in "Inventory Management" section

### Migration not running
- Delete database and recreate:
  ```bash
  mv data/cross_poster.db data/cross_poster.db.bak
  python gui.py  # Will create new database with new schema
  ```

## Future Enhancements

- Mobile app for scanning item locations with barcode
- Integration with label printers
- Heatmap showing which storage locations are most active
- Bulk edit storage locations
- Storage location suggestions based on item type
