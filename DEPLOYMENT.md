# Deployment Guide for Streamlit Cloud

## Quick Start

### Step 1: Prepare Your GitHub Repository

1. Go to https://github.com and log in
2. Click the "+" icon in top right, select "New repository"
3. Name your repository: `pilot-trip-analysis`
4. Choose Public or Private
5. DO NOT initialize with README (we have our own files)
6. Click "Create repository"

### Step 2: Upload Files to GitHub

You have two options:

#### Option A: Upload via GitHub Web Interface (Easiest)
1. On your new repository page, click "uploading an existing file"
2. Drag and drop ALL these files:
   - `app.py`
   - `analysis_engine.py`
   - `requirements.txt`
   - `README.md`
   - `.gitignore`
3. Create a new folder called `.streamlit` (click "Create new file", type `.streamlit/config.toml`)
4. Paste the contents of `config.toml`
5. Commit the changes

#### Option B: Upload via Git Command Line
```bash
# In your local directory with the files
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/pilot-trip-analysis.git
git push -u origin main
```

### Step 3: Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub (or create account)
3. Click "New app" button
4. Fill in the form:
   - **Repository**: Select `YOUR-USERNAME/pilot-trip-analysis`
   - **Branch**: main
   - **Main file path**: `app.py`
   - **App URL**: Choose a custom URL (optional)
5. Click "Deploy!"

### Step 4: Wait for Deployment

- Streamlit Cloud will install dependencies (takes 2-5 minutes)
- Watch the deployment logs in real-time
- Once done, you'll see "Your app is live!" message

### Step 5: Access Your App

Your app will be available at:
```
https://[your-app-name].streamlit.app
```

Share this URL with anyone who needs access!

## Post-Deployment

### Updating Your App

Any time you push changes to your GitHub repository, Streamlit Cloud will automatically redeploy your app.

To update:
1. Edit files locally or on GitHub
2. Commit and push changes
3. Streamlit Cloud will detect changes and redeploy (takes 1-2 minutes)

### Managing Your App

In Streamlit Cloud dashboard, you can:
- View app analytics
- Check logs for debugging
- Restart the app
- Delete the app
- Manage settings

### Monitoring Performance

Check the Streamlit Cloud dashboard for:
- Number of visitors
- CPU/memory usage
- Error logs
- Deployment history

## Troubleshooting Deployment

### Error: "requirements.txt not found"
- Make sure `requirements.txt` is in the root directory
- Check file name is exactly `requirements.txt` (lowercase)

### Error: "Module not found"
- Check that all packages are in `requirements.txt`
- Verify package names and versions are correct

### Error: "App crashed"
- Check logs in Streamlit Cloud dashboard
- Common issues:
  - Missing import statements
  - File path errors
  - Memory limits exceeded

### Error: "Port already in use" (local only)
- Use a different port: `streamlit run app.py --server.port 8502`

## File Size Considerations

### Streamlit Cloud Limits
- **File upload limit**: 200MB per file
- **Total app size**: 1GB (including dependencies)
- **Memory**: 1GB RAM (free tier)
- **CPU**: Shared resources

### Recommendations for Large Files
If you're working with very large files:

1. **Compress before upload**: The app can handle compressed data
2. **Use base filters**: Process subsets of data
3. **Consider upgrading**: Streamlit Cloud Teams plan offers more resources

## Security Notes

### Public vs Private Repos
- **Public repo**: Anyone can see your code (but not uploaded data)
- **Private repo**: Requires Streamlit Cloud Teams plan
- **Data security**: Uploaded files are processed in-memory only, not stored

### Sensitive Data
If working with sensitive data:
1. Don't commit actual data files to GitHub
2. Use private repository
3. Consider self-hosting instead of Streamlit Cloud

## Advanced Configuration

### Custom Domain
Streamlit Cloud Teams plan allows custom domains:
1. Go to app settings
2. Add your domain
3. Configure DNS records as instructed

### Environment Variables
If you need environment variables:
1. Create `.streamlit/secrets.toml` locally (don't commit!)
2. Add secrets in Streamlit Cloud dashboard
3. Access via `st.secrets` in code

### Resource Optimization
To optimize performance:
1. Use caching: `@st.cache_data` for data processing
2. Minimize file reads
3. Use efficient data structures (pandas DataFrames)
4. Lazy load large visualizations

## Cost Considerations

### Free Tier (Streamlit Community Cloud)
- ✅ Unlimited public apps
- ✅ 1GB RAM per app
- ✅ GitHub integration
- ✅ Automatic redeployment
- ❌ Limited to public repos
- ❌ Shared resources

### Teams Tier ($250/month)
- Everything in Free tier, plus:
- Private repositories
- More resources
- Priority support
- Custom domains
- SSO integration

## Support Resources

- **Streamlit Docs**: https://docs.streamlit.io
- **Streamlit Forum**: https://discuss.streamlit.io
- **GitHub Issues**: Create issues in your repository

## Next Steps

After deployment:
1. Test the app with sample data
2. Share the URL with your team
3. Gather feedback
4. Iterate on features
5. Monitor usage and performance

Congratulations! Your app is now live! 🎉
