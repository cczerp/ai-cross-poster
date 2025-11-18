# Linux Server Setup - Step by Step

## Simple Setup (5 Minutes)

### Step 1: Install Python (if not already installed)

```bash
sudo apt update
sudo apt install python3 python3-pip -y
```

### Step 2: Install Dependencies

```bash
cd ~/ai-cross-poster
pip3 install flask werkzeug python-dotenv
```

### Step 3: Set Secret Key

```bash
# Generate a random secret key
python3 -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))" >> .env
```

### Step 4: Run the Web App

```bash
python3 web_app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
```

### Step 5: Find Your IP Address

```bash
hostname -I
```

Example output: `192.168.1.100`

### Step 6: Access from Your Phone

1. Make sure your phone is on the same WiFi as your Linux computer
2. Open your phone's browser
3. Go to: `http://YOUR_IP:5000` (replace YOUR_IP with the number from step 5)
4. Example: `http://192.168.1.100:5000`

**🎉 You're done! The app should load on your phone!**

---

## Keep It Running (Background)

### Option A: Using screen (Simple)

```bash
# Install screen
sudo apt install screen -y

# Start a screen session
screen -S webapp

# Run the app
python3 web_app.py

# Detach (keep it running in background)
# Press: Ctrl+A then D

# To re-attach later:
screen -r webapp
```

### Option B: Auto-start on Boot (Better)

Create a startup service:

```bash
# Create service file
sudo nano /etc/systemd/system/ai-cross-poster.service
```

Paste this (replace `YOUR_USERNAME` with your username):

```ini
[Unit]
Description=AI Cross-Poster Web App
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/ai-cross-poster
Environment="PATH=/home/YOUR_USERNAME/.local/bin:/usr/bin"
ExecStart=/usr/bin/python3 web_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Save with: `Ctrl+X`, then `Y`, then `Enter`

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-cross-poster
sudo systemctl start ai-cross-poster
```

Check if it's running:

```bash
sudo systemctl status ai-cross-poster
```

Now it will:
- ✅ Start automatically when computer boots
- ✅ Restart automatically if it crashes
- ✅ Run in background

---

## Access from Internet (Optional)

### Using ngrok (Easiest Way)

Makes your app accessible from anywhere, even outside your home network.

**Step 1:** Sign up at https://ngrok.com (free)

**Step 2:** Install ngrok

```bash
# Download ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz

# Extract
tar -xvf ngrok-v3-stable-linux-amd64.tgz

# Move to system path
sudo mv ngrok /usr/local/bin/
```

**Step 3:** Authenticate (get token from ngrok.com dashboard)

```bash
ngrok authtoken YOUR_TOKEN_HERE
```

**Step 4:** Start ngrok

```bash
ngrok http 5000
```

You'll get a URL like: `https://abc123.ngrok.io`

**Now you can access the app from ANYWHERE using that URL!**

---

## Firewall Setup (If Needed)

If you can't access from phone, might need to open the port:

```bash
sudo ufw allow 5000
sudo ufw enable
```

---

## Troubleshooting

### Can't connect from phone?

1. **Check both devices on same WiFi:**
   - Computer WiFi: `iwconfig`
   - Phone: Check WiFi settings

2. **Check firewall:**
   ```bash
   sudo ufw status
   sudo ufw allow 5000
   ```

3. **Check IP address again:**
   ```bash
   hostname -I
   ```

4. **Ping from phone:**
   - Use a ping app on phone
   - Ping your computer's IP

### App won't start?

1. **Check for errors:**
   ```bash
   python3 web_app.py
   ```

2. **Check dependencies:**
   ```bash
   pip3 install flask werkzeug python-dotenv
   ```

3. **Check permissions:**
   ```bash
   mkdir -p data/uploads
   chmod 755 data/uploads
   ```

### Service won't start?

```bash
# Check logs
sudo journalctl -u ai-cross-poster -f

# Restart service
sudo systemctl restart ai-cross-poster
```

---

## Add to Phone Home Screen

Once you can access it on your phone:

**iPhone:**
1. Open in Safari
2. Tap share button (square with arrow)
3. Tap "Add to Home Screen"
4. Name it "AI Lister"
5. Tap "Add"

**Android:**
1. Open in Chrome
2. Tap menu (3 dots)
3. Tap "Add to Home screen"
4. Name it "AI Lister"
5. Tap "Add"

Now it acts like a native app!

---

## Quick Commands Reference

```bash
# Start app manually
python3 web_app.py

# Start with screen (background)
screen -S webapp
python3 web_app.py
# Ctrl+A then D to detach

# Service commands
sudo systemctl start ai-cross-poster    # Start
sudo systemctl stop ai-cross-poster     # Stop
sudo systemctl restart ai-cross-poster  # Restart
sudo systemctl status ai-cross-poster   # Check status

# View logs
sudo journalctl -u ai-cross-poster -f

# Find IP
hostname -I

# Check if port is open
sudo netstat -tuln | grep 5000
```

---

## Testing Checklist

- [ ] Web app starts without errors
- [ ] Can access from computer browser (localhost:5000)
- [ ] Can access from phone on same WiFi
- [ ] Can upload photos
- [ ] Can create listing
- [ ] Can save draft
- [ ] Storage location saves correctly
- [ ] Added to phone home screen

---

## Next Steps

Once working:
1. Create a test listing with photos
2. Add a storage location (B1, C2, etc.)
3. Save as draft
4. Test marking as sold
5. See how the storage location shows up!

---

## Need More Help?

1. Check the detailed deployment guide: `docs/WEB_APP_DEPLOYMENT.md`
2. Check Flask logs for errors
3. Make sure `.env` file has all required API keys
