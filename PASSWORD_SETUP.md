# Password Protection Setup Guide

## Overview

The app is now password-protected. Users must enter the correct password before accessing any features.

## For Local Development

### Step 1: Create secrets.toml

1. Copy the example file:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

2. Edit `.streamlit/secrets.toml` and set your password:
   ```toml
   APP_PASSWORD = "YourSecurePasswordHere"
   ```

3. The app will now require this password to access

### Step 2: Test Locally

1. Run the app:
   ```bash
   streamlit run app.py
   ```

2. You'll see a password prompt - enter your password

3. The password is remembered for the session

## For Streamlit Cloud Deployment

### Step 1: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io
2. Click "New app"
3. Connect your GitHub repository
4. Select the branch and main file (`app.py`)

### Step 2: Add Password to Secrets

1. In your app dashboard, click **"Settings"** (⚙️)
2. Click **"Secrets"** in the left sidebar
3. Add this content:
   ```toml
   APP_PASSWORD = "YourSecurePasswordHere"
   ```
4. Click **"Save"**

### Step 3: Share with Users

- Share the app URL with authorized users
- Give them the password separately (email, Slack, etc.)
- Users enter the password once per session

## Password Behavior

- **Entered Once**: Password is checked when the app loads
- **Session Persistence**: Once entered correctly, valid for the entire session
- **Auto-Clear**: Password is not stored permanently (cleared after check)
- **Default Fallback**: If no `APP_PASSWORD` is set in secrets, defaults to `pilot2026`

## Security Best Practices

✅ **DO:**
- Use a strong, unique password (12+ characters)
- Share password through secure channels (not in code/GitHub)
- Change password periodically
- Use different passwords for dev/prod environments

❌ **DON'T:**
- Commit secrets.toml to Git (it's gitignored by default)
- Share password in public channels
- Use the default password in production

## Changing the Password

### Local Development:
1. Edit `.streamlit/secrets.toml`
2. Change the `APP_PASSWORD` value
3. Restart the app

### Streamlit Cloud:
1. Go to app Settings > Secrets
2. Update the `APP_PASSWORD` value
3. Click Save
4. App will restart automatically

## Troubleshooting

### "Password incorrect" error
- Check for typos in the password
- Verify the password in secrets matches what you're entering
- Check that secrets.toml exists (local) or secrets are set (cloud)

### No password prompt appears
- The app may be using the default password (`pilot2026`)
- Check that `APP_PASSWORD` is set in secrets

### App immediately shows "Password incorrect"
- Clear your browser cache/cookies
- Open app in incognito/private browsing mode
- This resets the session state

## Example Deployment Workflow

```bash
# 1. Local testing
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your password
streamlit run app.py

# 2. Commit to GitHub (secrets.toml is gitignored)
git add .
git commit -m "Add password protection"
git push

# 3. Deploy on Streamlit Cloud
# - Go to share.streamlit.io
# - Connect repository
# - Add APP_PASSWORD to Secrets
# - Share URL + password with users
```

## Current Version

**Version 66.1** - Password Protection Added
- Password prompt on app load
- Session-based authentication
- Streamlit Cloud compatible
- Fallback to default password if not configured
