# Render Deployment Notes

## Database Connection Issues

If you're experiencing worker timeouts and SSL connection errors on Render, the issue is likely the DATABASE_URL.

### Solution: Use Render's Internal DATABASE_URL

Render provides TWO connection strings for PostgreSQL:

1. **External URL** (starts with `postgres://` from outside Render's network)
   - Slower, goes through public internet
   - Can have SSL handshake issues
   - Higher latency

2. **Internal URL** (starts with `postgresql://` within Render's private network)
   - Much faster
   - More reliable
   - Lower latency
   - **USE THIS ONE**

### How to Fix

1. Go to your Render Dashboard
2. Find your PostgreSQL database
3. Click "Info" tab
4. Look for **"Internal Database URL"** (not "External Database URL")
5. Copy the Internal URL
6. Update your web service's environment variable:
   - Set `DATABASE_URL` to the **Internal Database URL**

The internal URL typically looks like:
```
postgresql://user:password@dpg-xxxxx-internal.render.com/database
```

Note the `-internal` suffix in the hostname - that's the key difference!

### Why This Matters

- External URL can cause 6+ second response times
- Worker timeouts (SIGKILL after 120s)
- HTTP 499 errors (client gave up)
- Constant SSL connection drops

Using the internal URL should resolve all these issues and allow the app to start properly.
