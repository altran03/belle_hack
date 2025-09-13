import os
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
import httpx
from github_ops import GitHubOperations
from models.schemas import WebhookPayload, JobCreate
from models.database import get_db, Repository, User
from sqlalchemy.orm import Session

class WebhookHandler:
    def __init__(self):
        self.webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        if not self.webhook_secret:
            raise ValueError("GITHUB_WEBHOOK_SECRET environment variable is required")
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature using HMAC"""
        if not signature.startswith("sha256="):
            return False
        
        expected_signature = "sha256=" + hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    async def handle_push_webhook(self, request: Request) -> Dict[str, Any]:
        """Handle GitHub push webhook"""
        # Get signature from headers
        signature = request.headers.get("X-Hub-Signature-256")
        if not signature:
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Read payload
        payload = await request.body()
        
        # Verify signature
        if not self.verify_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        try:
            webhook_data = json.loads(payload.decode())
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Validate webhook data
        if not self._validate_webhook_data(webhook_data):
            raise HTTPException(status_code=400, detail="Invalid webhook data")
        
        # Extract repository information
        repo_info = webhook_data["repository"]
        owner = repo_info["owner"]["login"]
        repo_name = repo_info["name"]
        full_name = repo_info["full_name"]
        
        # Get the latest commit
        commits = webhook_data.get("commits", [])
        if not commits:
            return {"message": "No commits in push", "status": "ignored"}
        
        latest_commit = commits[-1]
        commit_sha = latest_commit["id"]
        
        # Check if this repository is monitored
        db = next(get_db())
        try:
            repository = db.query(Repository).filter(
                Repository.full_name == full_name
            ).first()
            
            if not repository or not repository.is_active:
                return {"message": "Repository not monitored", "status": "ignored"}
            
            # Create a new job
            job_data = JobCreate(
                repository_id=repository.id,
                commit_sha=commit_sha
            )
            
            # Trigger the analysis pipeline
            from pipeline import AnalysisPipeline
            pipeline = AnalysisPipeline()
            
            # Start the analysis in the background
            import asyncio
            asyncio.create_task(pipeline.run_analysis(job_data, repository, db))
            
            return {
                "message": "Analysis started",
                "status": "success",
                "repository": full_name,
                "commit": commit_sha
            }
            
        finally:
            db.close()
    
    def _validate_webhook_data(self, data: Dict[str, Any]) -> bool:
        """Validate webhook payload structure"""
        required_fields = ["ref", "repository", "commits", "after", "before"]
        
        for field in required_fields:
            if field not in data:
                return False
        
        # Validate repository structure
        repo = data["repository"]
        required_repo_fields = ["name", "full_name", "owner"]
        
        for field in required_repo_fields:
            if field not in repo:
                return False
        
        # Validate owner structure
        owner = repo["owner"]
        if "login" not in owner:
            return False
        
        return True
    
    async def get_webhook_info(self, owner: str, repo: str, access_token: str) -> Optional[Dict[str, Any]]:
        """Get webhook information for a repository"""
        github_ops = GitHubOperations(access_token)
        
        try:
            # This would require implementing a method to list webhooks
            # For now, return basic info
            return {
                "owner": owner,
                "repo": repo,
                "webhook_url": f"{os.getenv('WEBHOOK_BASE_URL', 'https://your-domain.com')}/api/webhooks/github"
            }
        except Exception as e:
            print(f"Error getting webhook info: {e}")
            return None