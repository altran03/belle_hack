import os
import uuid
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from collections import defaultdict
from time import time
from sqlalchemy.orm import Session
import httpx
import json
import secrets
from typing import Optional

from models.database import get_db, create_tables, User, Repository, Job
from models.schemas import (
    JobStatus, JobCreate, JobUpdate, GitHubOAuthResponse, 
    Repository as RepoSchema, Job as JobSchema, MonitorRepositoryRequest
)
from webhook_handler import WebhookHandler
from pipeline import AnalysisPipeline
from github_ops import GitHubOperations

# Authentication function
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current authenticated user from session"""
    # Get session ID from cookies
    session_id = request.cookies.get("session_id")
    
    if not session_id or session_id not in active_sessions:
        raise HTTPException(status_code=401, detail="No valid session found. Please authenticate with GitHub.")
    
    # Get user from session
    user_id = active_sessions[session_id]
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Session invalid. Please authenticate with GitHub.")
    
    return user

# Initialize FastAPI app
app = FastAPI(
    title="BugSniper Pro",
    description="AI-powered debugging agent for GitHub repositories",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware - only allow requests from trusted hosts
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.ngrok.io", "*.ngrok-free.app"]
)

# Simple rate limiting for webhook endpoint
webhook_requests = defaultdict(list)

@app.middleware("http")
async def rate_limit_webhook(request: Request, call_next):
    """Rate limit webhook endpoint to prevent abuse"""
    if request.url.path == "/api/webhooks/github":
        client_ip = request.client.host
        current_time = time()
        
        # Clean old requests (older than 1 minute)
        webhook_requests[client_ip] = [
            req_time for req_time in webhook_requests[client_ip] 
            if current_time - req_time < 60
        ]
        
        # Check if rate limit exceeded (max 10 requests per minute)
        if len(webhook_requests[client_ip]) >= 10:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Add current request
        webhook_requests[client_ip].append(current_time)
    
    response = await call_next(request)
    return response

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Initialize webhook handler
webhook_handler = WebhookHandler()

# Create database tables
create_tables()

# Environment variables
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_CALLBACK_URL = os.getenv("GITHUB_CALLBACK_URL", "http://localhost:8000/api/auth/github/callback")
SESSION_SECRET = os.getenv("SESSION_SECRET", "your-secret-key")

# Simple in-memory session storage (in production, use Redis or database)
active_sessions = {}  # session_id -> user_id

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    print("BugSniper Pro starting up...")
    print(f"GitHub Client ID: {GITHUB_CLIENT_ID}")
    print(f"Webhook Secret: {'Set' if os.getenv('GITHUB_WEBHOOK_SECRET') else 'Not set'}")

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "BugSniper Pro API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# User info endpoint
@app.get("/api/user")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "login": current_user.login,
        "name": current_user.name,
        "email": current_user.email,
        "avatar_url": current_user.avatar_url
    }

# GitHub OAuth endpoints
@app.get("/api/auth/github")
async def github_login():
    """Initiate GitHub OAuth flow"""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    state = str(uuid.uuid4())
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_CALLBACK_URL,
        "scope": "repo,user:email",
        "state": state
    }
    
    auth_url = "https://github.com/login/oauth/authorize?" + "&".join([f"{k}={v}" for k, v in params.items()])
    return RedirectResponse(url=auth_url)

@app.get("/api/auth/github/callback")
async def github_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Handle GitHub OAuth callback"""
    if not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    # Exchange code for access token
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code
            },
            headers={"Accept": "application/json"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
    
    # Get user information
    github_ops = GitHubOperations(access_token)
    user_info = await github_ops.get_user_info()
    
    # Create or update user
    user = db.query(User).filter(User.github_id == user_info["id"]).first()
    
    if user:
        user.access_token = access_token  # In production, encrypt this
        user.token_scope = token_data.get("scope", "")
        user.updated_at = datetime.utcnow()
    else:
        user = User(
            github_id=user_info["id"],
            login=user_info["login"],
            name=user_info.get("name"),
            email=user_info.get("email"),
            avatar_url=user_info.get("avatar_url"),
            access_token=access_token,  # In production, encrypt this
            token_scope=token_data.get("scope", "")
        )
        db.add(user)
    
    db.commit()
    db.refresh(user)
    
    # Create session
    session_id = secrets.token_urlsafe(32)
    active_sessions[session_id] = user.id
    
    # Redirect to frontend with success and set session cookie
    response = RedirectResponse(url=f"http://localhost:3000/auth/success?user_id={user.id}")
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=86400  # 24 hours
    )
    
    return response

# Logout endpoint
@app.post("/api/auth/logout")
async def logout(request: Request):
    """Logout user and clear session"""
    session_id = request.cookies.get("session_id")
    if session_id and session_id in active_sessions:
        del active_sessions[session_id]
    
    response = RedirectResponse(url="http://localhost:3000/")
    response.delete_cookie(key="session_id")
    return response

# Repository management endpoints
@app.get("/api/repositories")
async def get_repositories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's monitored repositories"""
    try:
        # Get monitored repositories from database
        repositories = db.query(Repository).filter(
            Repository.owner_id == current_user.id,
            Repository.is_active == True
        ).all()
        
        # Convert to dict format for JSON response
        result = []
        for repo in repositories:
            result.append({
                "id": repo.id,
                "github_id": repo.github_id,
                "name": repo.name,
                "full_name": repo.full_name,
                "owner_id": repo.owner_id,
                "default_branch": repo.default_branch,
                "clone_url": repo.clone_url,
                "webhook_url": repo.webhook_url,
                "webhook_secret": repo.webhook_secret,
                "webhook_id": repo.webhook_id,
                "is_active": repo.is_active,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
            })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_repositories: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/repositories/monitor")
async def add_repository_to_monitoring(
    request: MonitorRepositoryRequest,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Add a repository to monitoring"""
    try:
        owner = request.owner
        repo = request.repo
        
        # Check if repository already exists
        full_name = f"{owner}/{repo}"
        existing_repo = db.query(Repository).filter(
            Repository.full_name == full_name,
            Repository.owner_id == current_user.id
        ).first()
        
        if existing_repo:
            if existing_repo.is_active:
                return {"message": "Repository is already being monitored", "repository_id": existing_repo.id}
            else:
                # Reactivate existing repository
                existing_repo.is_active = True
                db.commit()
                return {"message": "Repository monitoring reactivated", "repository_id": existing_repo.id}
        
        # Check repository permissions and get info from GitHub
        github_ops = GitHubOperations(current_user.access_token)
        
        try:
            # Check if user has admin permissions (required for webhooks)
            repo_info = await github_ops.check_repository_permissions(owner, repo)
        except Exception as e:
            raise HTTPException(status_code=403, detail=str(e))
        
        # Set up webhook first (before creating database entry)
        webhook_url = f"{os.getenv('WEBHOOK_BASE_URL', 'https://a1663eee09f5.ngrok-free.app')}/api/webhooks/github"
        webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "your-webhook-secret")
        
        webhook_result = await github_ops.setup_webhook(owner, repo, webhook_url, webhook_secret)
        
        if not webhook_result:
            raise HTTPException(status_code=500, detail="Failed to set up webhook. Please check your WEBHOOK_BASE_URL and try again.")
        
        # Handle the case where webhook already exists
        if webhook_result.get("id") == "existing":
            print(f"Webhook already exists for {owner}/{repo}, continuing with setup...")
        
        # Create new repository entry with webhook info
        repository = Repository(
            github_id=repo_info["id"],
            name=repo_info["name"],
            full_name=full_name,
            owner_id=current_user.id,
            default_branch=repo_info.get("default_branch", "main"),
            clone_url=repo_info.get("clone_url"),
            is_active=True,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            webhook_id=webhook_result["id"] if webhook_result["id"] != "existing" else None
        )
        
        db.add(repository)
        db.commit()
        db.refresh(repository)
        
        webhook_message = "Repository added to monitoring with webhook"
        if webhook_result.get("id") == "existing":
            webhook_message = "Repository added to monitoring (webhook already existed)"
        
        return {
            "message": webhook_message, 
            "repository_id": repository.id, 
            "webhook_id": webhook_result["id"] if webhook_result["id"] != "existing" else "existing",
            "webhook_url": webhook_url
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add repository to monitoring: {str(e)}")

# GitHub repositories endpoint
@app.get("/api/github/repositories")
async def get_github_repositories(current_user: User = Depends(get_current_user)):
    """Get user's GitHub repositories"""
    try:
        if not current_user.access_token:
            raise HTTPException(status_code=401, detail="No GitHub access token found. Please authenticate with GitHub.")
        
        github_ops = GitHubOperations(current_user.access_token)
        repos = await github_ops.get_user_repositories(current_user.login)
        return repos
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {str(e)}")

@app.post("/api/repositories/{repo_id}/monitor")
async def start_monitoring(repo_id: int, db: Session = Depends(get_db)):
    """Start monitoring a repository"""
    repository = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    user = db.query(User).filter(User.id == repository.owner_id).first()
    if not user or not user.access_token:
        raise HTTPException(status_code=400, detail="User access token not found")
    
    # Set up webhook
    github_ops = GitHubOperations(user.access_token)
    owner, repo_name = repository.full_name.split("/", 1)
    
    webhook_url = f"{os.getenv('WEBHOOK_BASE_URL', 'https://your-domain.com')}/api/webhooks/github"
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    
    webhook_result = await github_ops.setup_webhook(owner, repo_name, webhook_url, webhook_secret)
    
    if webhook_result:
        repository.is_active = True
        repository.webhook_url = webhook_url
        repository.webhook_secret = webhook_secret
        db.commit()
        
        return {"message": "Monitoring started", "webhook_id": webhook_result["id"]}
    else:
        raise HTTPException(status_code=500, detail="Failed to set up webhook")

# Unmonitor repository endpoint
@app.delete("/api/repositories/{repo_id}/unmonitor")
async def unmonitor_repository(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop monitoring a repository"""
    repository = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    try:
        # Remove webhook from GitHub
        github_ops = GitHubOperations(current_user.access_token)
        if repository.webhook_id:
            await github_ops.delete_webhook(
                repository.full_name.split('/')[0], 
                repository.name, 
                repository.webhook_id
            )
        
        # Deactivate repository
        repository.is_active = False
        repository.webhook_id = None
        db.commit()
        
        return {"message": "Repository monitoring stopped", "repository": repository.full_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")

# Job management endpoints
@app.get("/api/jobs", response_model=List[JobSchema])
async def get_jobs(user_id: int, db: Session = Depends(get_db)):
    """Get user's jobs"""
    jobs = db.query(Job).filter(Job.user_id == user_id).order_by(Job.created_at.desc()).all()
    return jobs

@app.get("/api/jobs/{job_id}", response_model=JobSchema)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get specific job details"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Convert database fields to API schema format
    from models.schemas import PytestResult, GeminiAnalysis, Commit, DeployableStatus
    import json
    
    # Build Pytest result if data exists
    pytest_result = None
    if job.pytest_total_tests is not None:
        diagnostics = []
        if job.pytest_diagnostics:
            try:
                diagnostics = json.loads(job.pytest_diagnostics) if job.pytest_diagnostics.startswith('[') else [job.pytest_diagnostics]
            except:
                diagnostics = [job.pytest_diagnostics] if job.pytest_diagnostics else []
        
        pytest_result = PytestResult(
            passed=job.pytest_passed or False,
            total_tests=job.pytest_total_tests,
            failed_tests=job.pytest_failed_tests or 0,
            diagnostics=diagnostics,
            error_details=job.pytest_error_details,
            execution_time=job.pytest_execution_time or 0.0
        )
    
    # Build Gemini analysis if data exists
    gemini_analysis = None
    if job.gemini_issue_summary:
        bugs_detected = []
        optimizations = []
        
        if job.gemini_bugs_detected:
            try:
                bugs_detected = json.loads(job.gemini_bugs_detected)
            except:
                bugs_detected = [job.gemini_bugs_detected] if job.gemini_bugs_detected else []
        
        if job.gemini_optimizations:
            try:
                optimizations = json.loads(job.gemini_optimizations)
            except:
                optimizations = [job.gemini_optimizations] if job.gemini_optimizations else []
        
        gemini_analysis = GeminiAnalysis(
            issue_summary=job.gemini_issue_summary,
            bugs_detected=bugs_detected,
            optimizations=optimizations,
            patch=job.gemini_patch or "",
            deployable_status=DeployableStatus(job.gemini_deployable_status) if job.gemini_deployable_status else DeployableStatus.UNKNOWN,
            confidence_score=job.gemini_confidence_score or 0.0
        )
    
    # Build commit info if data exists
    commit = None
    if job.commit_message:
        commit = Commit(
            sha=job.commit_sha,
            message=job.commit_message,
            author=job.commit_author or "",
            author_email=job.commit_author_email or "",
            timestamp=job.commit_timestamp or datetime.utcnow(),
            url=job.commit_url or ""
        )
    
    # Return structured response
    return JobSchema(
        id=job.id,
        repository_id=job.repository_id,
        commit_sha=job.commit_sha,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        commit=commit,
        pytest_result=pytest_result,
        gemini_analysis=gemini_analysis,
        branch_name=job.branch_name,
        pr_url=job.pr_url,
        pr_number=job.pr_number
    )

@app.post("/api/jobs/{job_id}/approve")
async def approve_job(job_id: str, db: Session = Depends(get_db)):
    """Approve job and create pull request"""
    pipeline = AnalysisPipeline()
    result = await pipeline.approve_and_create_pr(job_id, db)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result["error"])

@app.post("/api/jobs/{job_id}/configure-pytest")
async def configure_pytest(job_id: str, db: Session = Depends(get_db)):
    """Trigger pytest configuration for a job"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get repository path
    repo = db.query(Repository).filter(Repository.id == job.repository_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # For now, return a message about pytest setup
    # In a real implementation, this could help set up pytest.ini or conftest.py
    return {
        "message": "Pytest configuration initiated",
        "config_url": f"https://docs.pytest.org/en/stable/getting-started.html?job_id={job_id}&repo={repo.name}",
        "status": "configuration_available"
    }

@app.delete("/api/jobs")
async def clear_job_history(user_id: int, db: Session = Depends(get_db)):
    """Clear all job history for a user"""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete all jobs for the user
    deleted_count = db.query(Job).filter(Job.user_id == user_id).delete()
    db.commit()
    
    return {"message": f"Cleared {deleted_count} jobs from history", "deleted_count": deleted_count}

# Webhook endpoint
@app.post("/api/webhooks/github")
async def github_webhook(request: Request):
    """Handle GitHub webhook"""
    return await webhook_handler.handle_push_webhook(request)

# Block GET requests to webhook endpoint
@app.get("/api/webhooks/github")
async def webhook_get_block(request: Request):
    """Block GET requests to webhook endpoint"""
    print(f"🚨 SECURITY ALERT: GET request blocked from {request.client.host} to webhook endpoint")
    raise HTTPException(status_code=405, detail="Method not allowed")

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back or handle specific messages
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)