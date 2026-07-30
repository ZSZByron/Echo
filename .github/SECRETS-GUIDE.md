# Echo Project GitHub Actions Secrets Configuration

## Required Secrets for CI/CD Pipeline

### Deployment Secrets
```
DEPLOY_HOST          - Your deployment server hostname
DEPLOY_USER          - SSH user for deployment
DEPLOY_KEY           - SSH private key for deployment access
BACKEND_URL          - Production backend URL for health checks
```

### Cloud Storage Secrets (Frontend)
```
AWS_ACCESS_KEY_ID    - AWS access key for S3 deployment
AWS_SECRET_ACCESS_KEY - AWS secret key for S3 deployment
AWS_REGION          - AWS region for S3 bucket
S3_BUCKET           - S3 bucket name for frontend hosting
```

### CDN Secrets (Optional)
```
CLOUDFLARE_API_TOKEN - Cloudflare API token for cache invalidation
CLOUDFLARE_ZONE_ID   - Cloudflare zone ID for your domain
```

### API Configuration
```
VITE_API_URL        - Frontend API endpoint URL
```

## How to Add Secrets to GitHub Repository

1. Go to your GitHub repository: https://github.com/ZSZByron/Echo
2. Navigate to: Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret from the list above
5. Click "Add secret" for each one

## Secret Values Reference

### Deployment Server Setup
```bash
# Generate SSH key for deployment
ssh-keygen -t ed25519 -C "github-actions" -f github_actions_key

# Add public key to your server
cat github_actions_key.pub | ssh user@your-server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# Use the private key content as DEPLOY_KEY secret
cat github_actions_key
```

### AWS S3 Setup (for frontend hosting)
```bash
# Create S3 bucket
aws s3 mb s3://your-frontend-bucket

# Create IAM user with S3 access
aws iam create-user --user-name github-actions-deploy

# Attach S3 policy
aws iam attach-user-policy --user-name github-actions-deploy --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Create access key
aws iam create-access-key --user-name github-actions-deploy
```

### Cloudflare Setup (optional)
1. Get API token: https://dash.cloudflare.com/profile/api-tokens
2. Find Zone ID in your domain's overview page

## Example Secret Values (Development Environment)

```
DEPLOY_HOST=dev-server.example.com
DEPLOY_USER=ubuntu
BACKEND_URL=https://api-dev.example.com
VITE_API_URL=https://api-dev.example.com
AWS_REGION=us-east-1
S3_BUCKET=echo-frontend-dev
```

## Security Notes

- Never commit secrets to the repository
- Rotate secrets regularly (recommended: every 90 days)
- Use minimal permission policies for deployment credentials
- Enable GitHub Actions secret scanning in repository settings
- Use environment-specific secrets for staging/production

## Testing Secrets Locally

Create a `.env.local` file for local testing (add to .gitignore):

```env
# Backend
ACTIVE_PROVIDER=openai
OPENAI_API_KEY=your-local-test-key

# Frontend
VITE_API_URL=http://localhost:8000
```

## Workflow Triggers

The workflows will run on:
- Push to `main` branch
- Pull requests to `main` branch  
- Manual dispatch via GitHub Actions UI
- Scheduled sync (daily at 2 AM UTC)