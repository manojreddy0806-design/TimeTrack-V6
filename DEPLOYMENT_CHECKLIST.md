# Vercel Deployment Checklist

## ✅ Pre-Deployment Setup

### 1. Files Created/Updated
- [x] `vercel.json` - Vercel configuration
- [x] `api/index.py` - Serverless function entry point
- [x] `.vercelignore` - Files to exclude from deployment
- [x] `.gitignore` - Updated with Vercel-specific ignores
- [x] `README_VERCEL.md` - Deployment guide

### 2. Environment Variables to Set in Vercel

Before deploying, set these in Vercel Dashboard → Project Settings → Environment Variables:

#### Required:
- [ ] `DATABASE_URL` - PostgreSQL connection string
  - Format: `postgresql://user:pass@host:port/dbname?sslmode=require`
  - Example: `postgresql://user:pass@dpg-xxxxx-a.oregon-postgres.render.com:5432/dbname?sslmode=require`

- [ ] `JWT_SECRET` - Secret for JWT token signing
  - Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

- [ ] `FLASK_ENV` - Set to `production`

#### Optional (if using payments):
- [ ] `STRIPE_SECRET_KEY` - Stripe secret key
- [ ] `STRIPE_PUBLISHABLE_KEY` - Stripe publishable key

### 3. Database Setup

- [ ] PostgreSQL database is running and accessible
- [ ] Database URL includes SSL mode: `?sslmode=require`
- [ ] Database firewall allows Vercel IPs (if applicable)
- [ ] Run database migrations (if needed)

### 4. Static Files

- [ ] Verify `frontend/static/` files are included
- [ ] Verify `frontend/pages/` HTML files are included
- [ ] Verify `landing/dist/public/` exists (if using landing page)

## 🚀 Deployment Steps

### Option A: Vercel CLI

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Login
vercel login

# 3. Navigate to project
cd timetrack

# 4. Deploy
vercel

# 5. Set environment variables
vercel env add DATABASE_URL
vercel env add JWT_SECRET
vercel env add FLASK_ENV production

# 6. Deploy to production
vercel --prod
```

### Option B: Vercel Dashboard

1. Push code to GitHub/GitLab/Bitbucket
2. Go to https://vercel.com/dashboard
3. Click "Add New Project"
4. Import your repository
5. Configure:
   - Framework: **Other**
   - Root Directory: `.`
   - Build Command: (leave empty)
   - Output Directory: (leave empty)
   - Install Command: `pip install -r requirements.txt`
6. Add environment variables
7. Deploy

## 🔍 Post-Deployment Testing

- [ ] Visit the deployed URL
- [ ] Test login functionality
- [ ] Test API endpoints (`/api/health`)
- [ ] Verify static files load (CSS, JS)
- [ ] Test HTML pages load correctly
- [ ] Check Vercel logs for errors

## ⚠️ Important Notes

1. **File Uploads**: The `uploads/` directory is not persisted. Consider using:
   - AWS S3
   - Cloudinary
   - Vercel Blob Storage

2. **Database Migrations**: May need to run separately. Options:
   - Use a migration service
   - Run via CLI in a separate environment
   - Use database migration tools

3. **Rate Limiting**: Currently uses in-memory storage. For production, consider Redis.

4. **Function Timeout**: Set to 30 seconds. Adjust in `vercel.json` if needed.

## 🐛 Troubleshooting

### Database Connection Issues
- Check `DATABASE_URL` format
- Verify SSL is enabled
- Check database firewall settings

### Import Errors
- Verify all dependencies in `requirements.txt`
- Check Python version (3.11)

### Static Files Not Loading
- Verify file paths in `backend/app.py`
- Check files exist in deployment

### View Logs
```bash
vercel logs
# Or in dashboard: Project → Functions → View logs
```

## 📝 Next Steps

After successful deployment:
1. Set up custom domain (optional)
2. Configure CI/CD for automatic deployments
3. Set up monitoring and alerts
4. Configure backup strategy for database

