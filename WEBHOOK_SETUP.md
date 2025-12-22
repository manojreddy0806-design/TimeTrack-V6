# Stripe Webhook Setup Guide

## Overview
Stripe webhooks are essential for completing the signup process. When a customer completes payment, Stripe sends a webhook event to your server to activate the account and send login credentials.

## Development Setup (Local)

For local development, use the Stripe CLI to forward webhooks:

```bash
stripe listen --forward-to http://localhost:5000/api/tenants/webhook/stripe
```

This will output a webhook signing secret (starts with `whsec_`). Set it in your `.env` file:

```bash
STRIPE_WEBHOOK_SECRET_DEV=whsec_xxxxxxxxxxxxx
```

**OR** you can use the regular webhook secret:

```bash
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

## Production Setup

For production, you need to configure webhooks in the Stripe Dashboard:

### Step 1: Get Your Production URL
Your production webhook endpoint should be:
```
https://your-domain.com/api/tenants/webhook/stripe
```

Replace `your-domain.com` with your actual deployed domain.

**Example for Vercel:**
If your Vercel deployment is at `time-track-v6.vercel.app`, your webhook URL is:
```
https://time-track-v6.vercel.app/api/tenants/webhook/stripe
```

**Note:** If you have a custom domain, use that instead (e.g., `https://yourdomain.com/api/tenants/webhook/stripe`)

### Step 1.5: Set Environment Variables in Vercel

Before configuring the webhook, make sure you have these environment variables set in Vercel:

1. Go to your Vercel project dashboard
2. Navigate to **Settings > Environment Variables**
3. Add these variables:

**Required:**
- `STRIPE_SECRET_KEY` = `sk_live_xxxxxxxxxxxxx` (your live Stripe secret key)
- `STRIPE_WEBHOOK_SECRET` = `whsec_xxxxxxxxxxxxx` (you'll get this after creating the webhook)
- `STRIPE_SUCCESS_URL` = `https://time-track-v6.vercel.app/signup-success?session_id={CHECKOUT_SESSION_ID}`
- `STRIPE_CANCEL_URL` = `https://time-track-v6.vercel.app/signup?cancelled=true`

**Also set:**
- `SMTP_USER` = your email
- `SMTP_PASSWORD` = your email app password
- `DATABASE_URL` = your PostgreSQL connection string
- All other required environment variables

**Important:** After adding environment variables, you need to **redeploy** your Vercel project for them to take effect.

### Step 2: Create Webhook in Stripe Dashboard

1. Go to [Stripe Dashboard > Developers > Webhooks](https://dashboard.stripe.com/webhooks)
2. Click **"Add endpoint"**
3. Enter your production webhook URL:
   ```
   https://your-domain.com/api/tenants/webhook/stripe
   ```
4. Select the event to listen for:
   - ✅ `checkout.session.completed`
   - ✅ `customer.subscription.updated` (optional, for plan changes)
   - ✅ `customer.subscription.deleted` (optional, for cancellations)
5. Click **"Add endpoint"**

### Step 3: Get Webhook Signing Secret

1. After creating the endpoint, click on it
2. In the "Signing secret" section, click **"Reveal"**
3. Copy the secret (starts with `whsec_`)

### Step 4: Set Environment Variable

Set the webhook secret in your production environment:

```bash
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

**Important:** This should be different from your development webhook secret.

## Environment Variables Summary

### Development
```bash
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx  # Test key
STRIPE_WEBHOOK_SECRET_DEV=whsec_xxxxxxxxxxxxx  # From stripe listen
STRIPE_SUCCESS_URL=http://localhost:5000/signup-success?session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=http://localhost:5000/signup?cancelled=true
```

### Production
```bash
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxx  # Live key
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx  # From Stripe Dashboard
STRIPE_SUCCESS_URL=https://your-domain.com/signup-success?session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=https://your-domain.com/signup?cancelled=true
```

## Testing Webhooks

### Test Locally
1. Run `stripe listen --forward-to http://localhost:5000/api/tenants/webhook/stripe`
2. In another terminal, trigger a test event:
   ```bash
   stripe trigger checkout.session.completed
   ```

### Test Production
1. Use Stripe Dashboard > Webhooks > Your endpoint > "Send test webhook"
2. Select `checkout.session.completed` event
3. Check your server logs to verify it was received

## Troubleshooting

### Webhook not received in production
- ✅ Verify webhook URL is accessible (not behind firewall)
- ✅ Check webhook secret is set correctly in environment variables
- ✅ Ensure HTTPS is used (Stripe requires HTTPS for production)
- ✅ Check server logs for webhook errors
- ✅ Verify webhook endpoint is registered in Stripe Dashboard

### Webhook signature verification failed
- ✅ Ensure `STRIPE_WEBHOOK_SECRET` matches the secret from Stripe Dashboard
- ✅ Don't mix development and production webhook secrets
- ✅ Check that the webhook payload hasn't been modified

### Signup completes but account not activated
- ✅ Check webhook logs in Stripe Dashboard (see delivery status)
- ✅ Check server logs for webhook processing errors
- ✅ Verify email configuration (SMTP settings) if credentials not sent

## Security Notes

- 🔒 Never commit webhook secrets to version control
- 🔒 Use environment variables for all secrets
- 🔒 Webhook secrets are different for development and production
- 🔒 Always verify webhook signatures (done automatically by the code)

