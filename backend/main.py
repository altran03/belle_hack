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
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import httpx
import json

from models.database import get_db, create_tables, User, Repository, Job
from models.schemas import (
    JobStatus, JobCreate, JobUpdate, GitHubOAuthResponse, 
    Repository as RepoSchema, Job as JobSchema, MonitorRepositoryRequest
)
from webhook_handler import WebhookHandler
from pipeline import AnalysisPipeline
from github_ops import GitHubOperations

# Authentication function
def get_current_user(db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
    # For now, we'll get the first authenticated user
    # In production, you'd validate JWT tokens or session data
    user = db.query(User).filter(User.access_token.isnot(None)).first()
    if not user:
        raise HTTPException(
            status_code=401, 
            detail="No authenticated user found. Please log in with GitHub first."
        )
    return user

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the application"""
    print("BugSniper Pro starting up...")
    print(f"GitHub Client ID: {GITHUB_CLIENT_ID}")
    print(f"Webhook Secret: {'Set' if os.getenv('GITHUB_WEBHOOK_SECRET') else 'Not set'}")
    
    # Create database tables
    create_tables()
    print("Database tables created")
    
    yield
    
    print("BugSniper Pro shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="BugSniper Pro",
    description="AI-powered debugging agent for GitHub repositories",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "BugSniper Pro API", "status": "running"}

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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

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
    async with httpx.AsyncClient() as client:
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
    
    # Redirect to frontend with success
    return RedirectResponse(url=f"http://localhost:3000/auth/success?user_id={user.id}")

# Repository management endpoints
@app.get("/api/repositories")
async def get_repositories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's monitored repositories"""
    try:
        if not current_user.access_token:
            raise HTTPException(status_code=400, detail="No access token found")
        
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
        
        # Get repository info from GitHub
        github_ops = GitHubOperations(current_user.access_token)
        repo_info = await github_ops.get_repository_info(owner, repo)
        
        # Create new repository entry
        repository = Repository(
            github_id=repo_info["id"],
            name=repo_info["name"],
            full_name=full_name,
            owner_id=current_user.id,
            default_branch=repo_info.get("default_branch", "main"),
            clone_url=repo_info.get("clone_url"),
            is_active=True
        )
        
        db.add(repository)
        db.commit()
        db.refresh(repository)
        
        # Set up webhook
        webhook_url = f"{os.getenv('WEBHOOK_BASE_URL', 'https://your-domain.com')}/api/webhooks/github"
        webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        
        webhook_result = await github_ops.setup_webhook(owner, repo, webhook_url, webhook_secret)
        
        if webhook_result:
            repository.webhook_url = webhook_url
            repository.webhook_secret = webhook_secret
            repository.webhook_id = webhook_result["id"]
            db.commit()
            
            return {"message": "Repository added to monitoring", "repository_id": repository.id, "webhook_id": webhook_result["id"]}
        else:
            # Repository was created but webhook failed
            repository.is_active = False
            db.commit()
            raise HTTPException(status_code=500, detail="Repository added but failed to set up webhook")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add repository to monitoring: {str(e)}")

@app.post("/api/repositories/{repo_id}/monitor")
async def start_monitoring(repo_id: int, db: Session = Depends(get_db)):
    """Start monitoring a repository (legacy endpoint)"""
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
        repository.webhook_id = webhook_result["id"]
        db.commit()
        
        return {"message": "Monitoring started", "webhook_id": webhook_result["id"]}
    else:
        raise HTTPException(status_code=500, detail="Failed to set up webhook")

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
    return job

@app.post("/api/jobs/{job_id}/approve")
async def approve_job(job_id: str, db: Session = Depends(get_db)):
    """Approve job and create pull request"""
    pipeline = AnalysisPipeline()
    result = await pipeline.approve_and_create_pr(job_id, db)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result["error"])

# GitHub repositories endpoint
@app.get("/api/github/repositories")
async def get_github_repositories(current_user: User = Depends(get_current_user)):
    """Get user's GitHub repositories"""
    try:
        github_ops = GitHubOperations(current_user.access_token)
        repos = await github_ops.get_user_repositories()
        return repos
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle other exceptions
        error_message = str(e)
        if "Invalid or expired access token" in error_message:
            raise HTTPException(status_code=401, detail="GitHub access token is invalid or expired")
        elif "Access token lacks required permissions" in error_message:
            raise HTTPException(status_code=403, detail="GitHub access token lacks required permissions")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {error_message}")

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
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    try:
        # Remove webhook from GitHub
        github_ops = GitHubOperations(current_user.access_token)
        if repository.webhook_id:
            await github_ops.delete_webhook(
                repository.owner, 
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

# Webhook endpoint
@app.post("/api/webhooks/github")
async def github_webhook(request: Request):
    """Handle GitHub webhook"""
    return await webhook_handler.handle_push_webhook(request)

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