# Fresh Start Instructions

## Before Sharing with Others

To clear your existing data and give everyone a fresh database:

### On Windows:

1. **Open PowerShell or Command Prompt**
2. **Navigate to your project folder:**
   ```bash
   cd C:\path\to\ai-cross-poster
   ```

3. **Run the clear script:**
   ```bash
   python clear_database.py
   ```

4. **Type exactly:** `DELETE ALL` when prompted

5. **Done!** Everyone now starts with a clean slate.

## What This Does

- ✅ Deletes all your test listings
- ✅ Clears draft photos
- ✅ Resets the database
- ✅ Everyone sees empty database when they connect

## Important Notes

- **Shared Database**: With your current setup, everyone accessing your server shares the same database
- This is **perfect for small teams** (you + a few friends)
- Everyone can create listings, and all listings are visible to all users
- **No extra work needed** - your friend just opens the ngrok URL and starts using it!

## When to Run This

- ✅ Before giving the app to your first friend
- ✅ If you want to wipe everything and start over
- ✅ Before deploying to production

## Alternative: Separate Instances

If you want each person to have **completely separate data**:
- Each person needs to run their own copy of the app (on their own computer/Raspberry Pi)
- This requires each person to do the full setup
- **You said you don't want this** - so stick with the shared database approach!

---

**Your current approach (shared hosting) is perfect for:**
- Small teams
- Friends/family helping each other
- Testing and getting started
- Minimal complexity
