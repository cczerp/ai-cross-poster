# Web App Deployment Guide

## Deploy on Raspberry Pi or Linux Computer

### Option 1: Local Network Access (Easiest)

Access from your phone on the same WiFi network.

**Steps:**

1. **Install dependencies:**
```bash
cd /home/user/ai-cross-poster
pip install -r requirements-web.txt
```

2. **Run the web app:**
```bash
python web_app.py
```

3. **Access from your phone:**
   - Find your computer's IP address:
     ```bash
     hostname -I
     ```
   - On your phone, open browser and go to:
     ```
     http://YOUR_IP_ADDRESS:5000
     ```
   - Example: `http://192.168.1.100:5000`

4. **Keep it running:**
   - Use `screen` or `tmux` to keep it running:
     ```bash
     screen -S webapp
     python web_app.py
     # Press Ctrl+A then D to detach
     ```

---

### Option 2: Internet Access (Advanced)

Make it accessible from anywhere on the internet.

#### Using ngrok (Quick & Easy)

1. **Install ngrok:**
```bash
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz
tar -xvf ngrok-v3-stable-linux-arm64.tgz
sudo mv ngrok /usr/local/bin/
```

2. **Sign up at https://ngrok.com and get your auth token**

3. **Authenticate:**
```bash
ngrok authtoken YOUR_AUTH_TOKEN
```

4. **Run web app and expose it:**
```bash
# Terminal 1: Run the app
python web_app.py

# Terminal 2: Expose it
ngrok http 5000
```

5. **Access from anywhere:**
   - ngrok will give you a URL like: `https://abc123.ngrok.io`
   - Open that URL on any device, anywhere!

---

#### Using systemd (Production)

Run as a system service that starts automatically.

1. **Create service file:**
```bash
sudo nano /etc/systemd/system/ai-cross-poster.service
```

2. **Add this content:**
```ini
[Unit]
Description=AI Cross-Poster Web App
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/user/ai-cross-poster
Environment="PATH=/home/user/.local/bin:/usr/bin"
ExecStart=/usr/bin/python3 web_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. **Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-cross-poster
sudo systemctl start ai-cross-poster
```

4. **Check status:**
```bash
sudo systemctl status ai-cross-poster
```

---

#### Using Your Domain (Optional)

If you have a domain name:

1. **Install Nginx:**
```bash
sudo apt install nginx
```

2. **Configure Nginx:**
```bash
sudo nano /etc/nginx/sites-available/ai-cross-poster
```

Add:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. **Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/ai-cross-poster /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

4. **Add SSL (HTTPS):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

### Option 3: Run in Production Mode

Use gunicorn for better performance:

1. **Install gunicorn:**
```bash
pip install gunicorn
```

2. **Run with gunicorn:**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
```

---

## Security Considerations

### IMPORTANT: Change Secret Key

Before deploying to internet, change the Flask secret key:

1. **Generate a secure key:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

2. **Add to `.env` file:**
```bash
FLASK_SECRET_KEY=your_generated_key_here
```

### Additional Security

1. **Use HTTPS** (with Let's Encrypt/certbot)
2. **Add authentication** if multiple users
3. **Set up firewall:**
```bash
sudo ufw allow 5000
sudo ufw enable
```

---

## Troubleshooting

### Can't access from phone?

- Check firewall: `sudo ufw status`
- Check IP address: `hostname -I`
- Make sure both devices are on same WiFi

### App crashes?

- Check logs: `sudo journalctl -u ai-cross-poster -f`
- Check permissions on data folders

### Photos not uploading?

- Check upload folder exists: `mkdir -p data/uploads`
- Check permissions: `chmod 755 data/uploads`

---

## Mobile Browser Tips

### Add to Home Screen

**iPhone:**
1. Open in Safari
2. Tap Share button
3. "Add to Home Screen"
4. Now it acts like an app!

**Android:**
1. Open in Chrome
2. Tap menu (3 dots)
3. "Add to Home screen"
4. Now it acts like an app!

### Camera Access

The web app will ask for camera permission when you select photos. Grant it to use your phone's camera directly.

---

## Raspberry Pi Specific Tips

### Auto-start on boot

1. Add to `/etc/rc.local` before `exit 0`:
```bash
cd /home/user/ai-cross-poster && python3 web_app.py &
```

2. Or use systemd (recommended - see above)

### Performance

- Raspberry Pi 3/4 works great
- Pi Zero might be slow with AI features
- Consider adding swap if you have <2GB RAM

### Remote Access

Use SSH to manage remotely:
```bash
ssh pi@YOUR_IP_ADDRESS
```

---

## Quick Start Checklist

- [ ] Install Python dependencies
- [ ] Set Flask secret key in .env
- [ ] Run `python web_app.py`
- [ ] Find IP address with `hostname -I`
- [ ] Open `http://YOUR_IP:5000` on phone
- [ ] Add to home screen
- [ ] Test photo upload
- [ ] Test creating listing

---

## Need Help?

- Check app logs for errors
- Make sure all environment variables are set
- Test desktop GUI first to verify backend works
- Ensure photo directories exist and have permissions
