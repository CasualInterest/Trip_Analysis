# Setting Up Your Anthropic API Key

## For Streamlit Cloud (Recommended)

1. **Deploy your app** to Streamlit Cloud (share.streamlit.io)

2. **Go to your app's settings:**
   - Click on your app
   - Click the menu (⋮) in the bottom right
   - Select "Settings"

3. **Add your secret:**
   - Click "Secrets" in the left sidebar
   - Paste this (with your real API key):
     ```toml
     ANTHROPIC_API_KEY = "sk-ant-your-actual-key-here"
     ```
   - Click "Save"

4. **Done!** Your app will automatically use the API key. No need to enter it every time!

## For Local Development

1. **Copy the template:**
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

2. **Edit `.streamlit/secrets.toml`:**
   - Replace `"sk-ant-your-api-key-here"` with your actual API key

3. **Done!** The app will auto-load your key when running locally.

## Getting Your API Key

1. Go to https://console.anthropic.com
2. Sign up or log in
3. Go to "API Keys" section
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-...`)

## Security Notes

- ✅ `secrets.toml` is in `.gitignore` - it won't be committed to git
- ✅ Streamlit Cloud secrets are encrypted and secure
- ✅ Never share your API key publicly
- ✅ If you accidentally expose your key, delete it and create a new one

## Fallback

If you don't set up secrets, the app will still work! You'll just need to enter your API key in the text box each time you use the AI feature. The key will be saved for your current session.
