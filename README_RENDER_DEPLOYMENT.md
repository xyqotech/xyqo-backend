# XYQO Backend - Render Deployment Guide

## 🚀 Migration from Railway to Render

### Files Created/Modified for Render:
- `render.yaml` - Render service configuration
- `.env.example` - Environment variables template
- `app.py` - Updated with Render-optimized settings

### Deployment Steps:

1. **Create Render Account**: Sign up at render.com
2. **Connect GitHub**: Link your repository
3. **Create Web Service**: 
   - Choose "Web Service"
   - Connect repository: `xyqo-home`
   - Root directory: `backend`
   - Build command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start command: `python app.py`

4. **Environment Variables** (Critical):
   ```
   OPENAI_API_KEY=your_actual_openai_key
   ALLOWED_ORIGINS=https://your-frontend.vercel.app
   PYTHONUNBUFFERED=1
   ```

5. **Service Configuration**:
   - Plan: Starter ($7/month) or Professional ($25/month)
   - Region: Oregon (recommended)
   - Health check: `/health`
   - Auto-deploy: Enable

### Key Improvements over Railway:
- **Persistent workers** (no cold starts)
- **Longer timeouts** (65s keep-alive for OpenAI processing)
- **Better logging** and error handling
- **Stable networking** (no 502 errors)
- **Predictable pricing**

### Testing Endpoints:
- Health: `https://your-app.onrender.com/health`
- Analyze: `POST https://your-app.onrender.com/api/v1/contract/analyze`
- Download: `GET https://your-app.onrender.com/api/v1/contract/download/{analysis_id}`

### Frontend Integration:
Update your frontend environment variables:
```
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
```

## 🔧 Troubleshooting:
- Check logs in Render dashboard
- Verify environment variables are set
- Ensure OpenAI API key is valid
- Test health endpoint first
