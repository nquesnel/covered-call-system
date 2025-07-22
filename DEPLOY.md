# Deployment Guide for Covered Call System

## 🚀 Quick Deploy to Render (Recommended)

### Prerequisites
1. GitHub account
2. Render account (free at render.com)

### Steps

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial covered call system"
   git branch -M main
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Render:**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Use these settings:
     - **Name**: covered-call-system
     - **Environment**: Python
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

3. **Add Environment Variables in Render:**
   - Go to your service's "Environment" tab
   - Add these keys (get free API keys from providers):
     ```
     YAHOO_FINANCE_API_KEY=your_key_here
     UNUSUAL_WHALES_API_KEY=your_key_here
     TD_AMERITRADE_API_KEY=your_key_here
     ANTHROPIC_API_KEY=your_key_here
     ```

4. **Access Your App:**
   - Your app will be live at: `https://covered-call-system.onrender.com`

## 🌊 Alternative: Streamlit Cloud (Easiest)

1. **Push to GitHub** (same as above)

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your GitHub repo
   - Choose `main` branch
   - Set main file path: `app.py`
   - Click "Deploy"

3. **Add Secrets:**
   - In Streamlit Cloud dashboard, go to "Settings" → "Secrets"
   - Add your API keys in TOML format:
   ```toml
   YAHOO_FINANCE_API_KEY = "your_key_here"
   UNUSUAL_WHALES_API_KEY = "your_key_here"
   ANTHROPIC_API_KEY = "your_key_here"
   ```

## 🏗️ Alternative: Railway ($5/month)

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Deploy:**
   ```bash
   railway login
   railway init
   railway up
   ```

3. **Add Variables:**
   - Go to your Railway dashboard
   - Add environment variables
   - Railway handles SSL and domains automatically

## 🔐 Security Notes

- **Never commit API keys** to GitHub
- Use environment variables for all secrets
- Enable 2FA on your deployment platform
- Consider IP whitelisting if available

## 📱 After Deployment

### Features Enabled by Cloud Deployment:
1. **Screenshot parsing with Claude Vision** - Add ANTHROPIC_API_KEY
2. **Real-time whale flows** - Add UNUSUAL_WHALES_API_KEY
3. **Auto-execution** - Add TD_AMERITRADE_API_KEY
4. **Access from anywhere** - Use on phone, tablet, etc.

### Mobile Access:
- Save as home screen app on iPhone/Android
- Works great on tablets for monitoring
- Real-time updates from any device

## 🆘 Troubleshooting

**App not starting?**
- Check logs in Render/Streamlit dashboard
- Ensure all dependencies in requirements.txt
- Verify Python version matches

**Data not persisting?**
- Cloud deployments reset on restart
- Consider adding PostgreSQL for permanent storage
- Or use Streamlit Cloud's persistent storage

**Slow performance?**
- Upgrade to paid tier for better resources
- Implement caching for API calls
- Reduce data fetch frequency

## 📊 Monitoring

After deployment, monitor:
- Response times
- Error rates  
- API usage limits
- Monthly costs

Your covered call system will be accessible 24/7 from any device!