# PhotoSync Integration Guide 📸

This guide shows you how to integrate PhotoSync with AI Cross-Poster for seamless photo workflow from phone to listings.

## What is PhotoSync?

[PhotoSync](https://www.photosync-app.com/) is an app that automatically transfers photos and videos from your phone to your computer. Perfect for resellers who take product photos on their phone!

## Setup Instructions

### 1. Install PhotoSync

**On Your Phone:**
- Download PhotoSync from App Store (iOS) or Google Play (Android)
- Open the app and grant photo permissions

**On Your Computer:**
- Download PhotoSync companion app (optional but recommended)
- Or use any of these transfer methods:
  - SMB/Windows Share
  - FTP
  - WebDAV
  - Computer folder sync

### 2. Configure PhotoSync Transfer Location

Set up PhotoSync to save photos to your AI Cross-Poster images folder:

**Recommended folder structure:**
```
ai-cross-poster/
├── images/
│   ├── new_items/          ← PhotoSync saves here
│   ├── processed/          ← Move photos here after creating listing
│   └── archive/            ← Archive old photos
```

**PhotoSync Settings:**
1. Open PhotoSync app on your phone
2. Tap "Configure" or "Settings"
3. Select transfer target (Computer, NAS, Cloud, etc.)
4. Set destination folder to: `ai-cross-poster/images/new_items/`
5. Enable "Auto Transfer" (optional - transfers photos automatically)

### 3. Update AI Cross-Poster Configuration

Edit your `.env` file:

```bash
# PhotoSync Configuration
PHOTOSYNC_FOLDER=./images/new_items
AUTO_PROCESS_PHOTOS=false
```

### 4. Create the Images Directory

```bash
cd ai-cross-poster
mkdir -p images/new_items images/processed images/archive
```

## Workflow: From Phone to Listing

### Option 1: Manual Workflow (Recommended)

1. **Take photos** on your phone of the item
2. **Transfer photos** using PhotoSync to `images/new_items/`
3. **Run AI Cross-Poster:**
   ```bash
   python main.py
   ```
4. **Select option 2:** "Create Listing from Photos (AI Analysis)"
5. **Enter photo paths:**
   ```
   Photo #1: ./images/new_items/item1_front.jpg
   Photo #2: ./images/new_items/item1_back.jpg
   Photo #3: ./images/new_items/item1_tag.jpg
   ```
6. **AI analyzes photos** and generates listing
7. **Review and publish**
8. **Move photos** to processed folder:
   ```bash
   mv images/new_items/item1_*.jpg images/processed/
   ```

### Option 2: Batch Workflow

For creating multiple listings at once:

1. **Organize photos** in PhotoSync folder by item:
   ```
   images/new_items/
   ├── item1_photo1.jpg
   ├── item1_photo2.jpg
   ├── item2_photo1.jpg
   ├── item2_photo2.jpg
   ```

2. **Use the batch example:**
   ```python
   from pathlib import Path
   from src.schema import UnifiedListing, Photo, Price, ListingCondition
   from src.publisher import publish_to_all

   # Get photos from PhotoSync folder
   photosync_folder = Path("./images/new_items")

   # Group photos by item (assumes naming like item1_photo1.jpg)
   items = {}
   for photo_file in photosync_folder.glob("*.jpg"):
       item_name = photo_file.stem.split('_')[0]  # Get "item1" from "item1_photo1"
       if item_name not in items:
           items[item_name] = []
       items[item_name].append(str(photo_file))

   # Create listings for each item
   for item_name, photo_paths in items.items():
       photos = [
           Photo(local_path=path, order=i, is_primary=(i==0))
           for i, path in enumerate(sorted(photo_paths))
       ]

       listing = UnifiedListing(
           title="AI Generated",
           description="AI Generated",
           price=Price(amount=0.0),  # Will be set manually
           condition=ListingCondition.GOOD,
           photos=photos,
       )

       # AI will analyze and enhance
       results = publish_to_all(listing)
       print(f"✅ Published {item_name}: {results}")
   ```

### Option 3: Watch Folder (Advanced)

Create a script that monitors the PhotoSync folder and auto-creates listings:

```python
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PhotoSyncHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(('.jpg', '.jpeg', '.png')):
            print(f"New photo detected: {event.src_path}")
            # Add to queue for processing

# Set up file watcher
observer = Observer()
observer.schedule(PhotoSyncHandler(), "./images/new_items", recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

## Tips for Best Results

### Photo Tips

1. **Take multiple angles:**
   - Front view (primary photo)
   - Back view
   - Close-up of brand tag/label
   - Any defects or wear
   - Size tag (if clothing)

2. **Good lighting:**
   - Natural daylight is best
   - Avoid harsh shadows
   - Use consistent background

3. **Clear focus:**
   - Make sure brand names are readable
   - Labels and tags should be in focus
   - Show condition clearly

### Naming Convention

Use consistent naming for easier organization:
```
images/new_items/
├── nike_shoes_001_front.jpg
├── nike_shoes_001_back.jpg
├── nike_shoes_001_tag.jpg
├── levi_jeans_002_front.jpg
├── levi_jeans_002_tag.jpg
```

### PhotoSync Settings for Best Performance

**Recommended settings:**
- ✅ **Transfer original photos** (don't compress)
- ✅ **Preserve metadata** (EXIF data can help AI)
- ✅ **Auto-transfer** when on WiFi
- ✅ **Delete after transfer** (optional - saves phone space)
- ❌ **Don't resize photos** (keep full resolution)

## Troubleshooting

### PhotoSync not transferring

1. Check WiFi connection (both devices on same network)
2. Verify folder permissions
3. Check firewall settings
4. Test with manual transfer first

### AI not recognizing photos

1. Ensure photos are in supported formats (JPG, PNG)
2. Check file paths are correct
3. Verify photos aren't corrupted
4. Make sure brand labels are visible and in focus

### Photos not found error

```bash
# Check if files exist
ls -la images/new_items/

# Check permissions
chmod -R 755 images/

# Verify path in .env
cat .env | grep PHOTOSYNC_FOLDER
```

## Advanced: Auto-Organize Script

Create `scripts/organize_photos.py`:

```python
#!/usr/bin/env python3
"""
Automatically organize photos from PhotoSync folder
Groups photos by timestamp/batch for easier listing creation
"""
import os
import shutil
from pathlib import Path
from datetime import datetime

def organize_photos(source_folder="./images/new_items", dest_folder="./images/organized"):
    source = Path(source_folder)
    dest = Path(dest_folder)

    # Get all photos
    photos = sorted(source.glob("*.{jpg,jpeg,png,JPG,JPEG,PNG}"))

    # Group by 5-minute intervals (photos taken together)
    batches = []
    current_batch = []
    last_time = None

    for photo in photos:
        # Get file modification time
        mtime = datetime.fromtimestamp(photo.stat().st_mtime)

        if last_time is None or (mtime - last_time).total_seconds() < 300:
            current_batch.append(photo)
        else:
            if current_batch:
                batches.append(current_batch)
            current_batch = [photo]

        last_time = mtime

    if current_batch:
        batches.append(current_batch)

    # Move batches to organized folders
    for i, batch in enumerate(batches, 1):
        batch_folder = dest / f"item_{i:03d}"
        batch_folder.mkdir(parents=True, exist_ok=True)

        for j, photo in enumerate(batch, 1):
            dest_path = batch_folder / f"photo_{j:02d}{photo.suffix}"
            shutil.move(str(photo), str(dest_path))
            print(f"Moved: {photo.name} → {dest_path}")

    print(f"\n✅ Organized {len(photos)} photos into {len(batches)} items")

if __name__ == "__main__":
    organize_photos()
```

Run it:
```bash
python scripts/organize_photos.py
```

## Integration with Main App

The main app already supports PhotoSync workflow! When you choose "Create Listing from Photos", just provide paths from your PhotoSync folder:

```bash
$ python main.py

Select option: 2
Photo #1: ./images/new_items/item_front.jpg
Photo #2: ./images/new_items/item_back.jpg
...
```

The AI will analyze the photos and create a complete listing automatically!

---

**Questions or issues?** Check out [PhotoSync support](https://www.photosync-app.com/support) or open an issue in this repository.
