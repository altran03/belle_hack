# BugSniper Pro - AI-Powered Debugging Agent

BugSniper Pro is a comprehensive AI agent that automatically detects bugs, analyzes code quality, and generates fixes for GitHub repositories. It integrates with TestSprite for automated testing and uses Google Gemini for AI-powered analysis.

## 🎯 Features

- **GitHub OAuth Integration**: Secure authentication with repository access
- **Webhook Monitoring**: Real-time detection of new pushes
- **AI-Powered Analysis**: Uses Google Gemini to detect bugs and generate fixes
- **Automated Testing**: Integrates with TestSprite for comprehensive testing
- **Patch Generation**: Creates unified diff patches for code fixes
- **Pull Request Automation**: Automatically creates PRs with fixes
- **Real-time Dashboard**: WebSocket-powered live updates
- **Deployable Status**: Determines if code is ready for deployment

## 🏗️ Architecture

### Backend (FastAPI)
- **REST API**: Core endpoints for job management and GitHub operations
- **WebSocket**: Real-time job updates and log streaming
- **OAuth Flow**: Secure GitHub authentication
- **Webhook Handler**: HMAC-verified GitHub webhook processing
- **Analysis Pipeline**: Orchestrates the detect→fix→test→review workflow
- **Database**: SQLite for job tracking and user management

### Frontend (Next.js)
- **Dashboard**: Overview of jobs and repositories
- **Job Details**: Detailed view with diff viewer and logs
- **Real-time Updates**: WebSocket integration for live status
- **Responsive Design**: TailwindCSS for modern UI

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- GitHub OAuth App
- Google Gemini API Key
- TestSprite API Key (optional for mock mode)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd bugsniper-pro
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Environment Configuration

Copy the example environment file:

```bash
cp env.example .env
```

Edit `.env` with your configuration:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here
GITHUB_CLIENT_ID=your_app_client_id
GITHUB_CLIENT_SECRET=your_app_client_secret
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Optional (for development)
GEMINI_MOCK=1
TESTSPRITE_MOCK=1
```

### 5. GitHub OAuth App Setup

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create a new OAuth App with:
   - **Application name**: BugSniper Pro
   - **Homepage URL**: `http://localhost:3000`
   - **Authorization callback URL**: `http://localhost:8000/api/auth/github/callback`
3. Copy the Client ID and Client Secret to your `.env` file

### 6. Run the Application

**Backend:**
```bash
cd backend
python main.py
```

**Frontend:**
```bash
cd frontend
npm run dev
```

**Webhook Testing (with ngrok):**
```bash
# Install ngrok
npm install -g ngrok

# Expose local server
ngrok http 8000

# Update WEBHOOK_BASE_URL in .env with ngrok URL
```

## 🔧 Development Mode

For development and testing, you can use mock modes:

```env
GEMINI_MOCK=1        # Use mock Gemini responses
TESTSPRITE_MOCK=1    # Use mock TestSprite responses
```

This allows you to test the full workflow without API keys.

## 📋 Usage Workflow

### 1. Authentication
- Visit `http://localhost:3000`
- Click "Connect GitHub"
- Authorize the application

### 2. Repository Setup
- Select repositories to monitor
- Enable webhook monitoring
- Repository will be added to your dashboard

### 3. Automatic Analysis
- Push commits to monitored repositories
- BugSniper Pro automatically detects the push
- Analysis pipeline runs in the background:
  - Downloads commit snapshot
  - Runs TestSprite analysis
  - Generates AI-powered fixes
  - Tests the fixes

### 4. Review and Approve
- View analysis results in the dashboard
- Review detected issues and generated patches
- Click "Approve & Create PR" to deploy fixes
- Pull request is automatically created

## 🧪 Testing with Sample Repository

The project includes a sample repository (`sample_repo/`) with deliberate bugs:

1. Push the sample repository to GitHub
2. Connect it to BugSniper Pro
3. Make a commit to trigger analysis
4. Review the detected issues and generated fixes

### Sample Issues Included:
- Security vulnerabilities (`eval()`, `exec()`)
- Code quality issues (missing docstrings, unused imports)
- Performance problems (inefficient algorithms)
- Error handling issues (bare except clauses)
- Python 2 compatibility issues

## 🔒 Security Features

- **HMAC Verification**: All webhooks are verified using GitHub's signature
- **Token Encryption**: OAuth tokens are encrypted in the database
- **Ephemeral Workspaces**: Analysis runs in temporary directories
- **No Auto-Commits**: Never commits directly to default branches
- **User Approval**: All fixes require explicit user approval

## 📊 API Endpoints

### Authentication
- `GET /api/auth/github` - Initiate OAuth flow
- `GET /api/auth/github/callback` - OAuth callback

### Repositories
- `GET /api/repositories` - List user repositories
- `POST /api/repositories/{id}/monitor` - Start monitoring

### Jobs
- `GET /api/jobs` - List user jobs
- `GET /api/jobs/{id}` - Get job details
- `POST /api/jobs/{id}/approve` - Approve and create PR

### Webhooks
- `POST /api/webhooks/github` - GitHub webhook endpoint

### WebSocket
- `WS /ws/{user_id}` - Real-time job updates

## 🛠️ Configuration Options

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `GITHUB_CLIENT_ID` | GitHub OAuth app client ID | Yes |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app client secret | Yes |
| `GITHUB_WEBHOOK_SECRET` | Webhook verification secret | Yes |
| `TESTSPRITE_API_KEY` | TestSprite API key | No (mock mode) |
| `DATABASE_URL` | Database connection string | No (defaults to SQLite) |
| `WEBHOOK_BASE_URL` | Base URL for webhooks | Yes (for production) |

### Mock Modes

Set these to `1` for development without API keys:
- `GEMINI_MOCK=1` - Use mock Gemini responses
- `TESTSPRITE_MOCK=1` - Use mock TestSprite responses

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**: Set all required environment variables
2. **Database**: Use PostgreSQL or MySQL for production
3. **Redis**: Set up Redis for background job processing
4. **HTTPS**: Ensure all webhook URLs use HTTPS
5. **Secrets**: Use proper secret management (AWS Secrets Manager, etc.)
6. **Monitoring**: Set up logging and monitoring
7. **Scaling**: Use multiple workers for high throughput

### Docker Deployment

```dockerfile
# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["python", "main.py"]

# Frontend Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build
CMD ["npm", "start"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Webhook not triggering**: Check ngrok URL and webhook secret
2. **OAuth errors**: Verify callback URL matches GitHub app settings
3. **API key errors**: Check environment variables and API key validity
4. **Database errors**: Ensure SQLite file permissions are correct

### Debug Mode

Enable debug logging:

```env
ENVIRONMENT=development
DEBUG=1
```

### Logs

Check application logs for detailed error information:

```bash
# Backend logs
tail -f backend/logs/app.log

# Frontend logs
npm run dev  # Check console output
```

## 📞 Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section
- Review the API documentation

---

**BugSniper Pro** - Making code debugging effortless with AI power! 🐛✨