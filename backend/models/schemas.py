from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    TESTING = "testing"
    FIXING = "fixing"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"

class DeployableStatus(str, Enum):
    DEPLOYABLE = "deployable"
    NOT_DEPLOYABLE = "not_deployable"
    UNKNOWN = "unknown"

class GitHubUser(BaseModel):
    id: int
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None

class Repository(BaseModel):
    id: int
    github_id: int
    name: str
    full_name: str
    owner: str
    default_branch: str
    clone_url: str
    webhook_url: Optional[str] = None
    is_active: bool = True

class Commit(BaseModel):
    sha: str
    message: str
    author: str
    author_email: str
    timestamp: datetime
    url: str

class TestSpriteResult(BaseModel):
    passed: bool
    total_tests: int
    failed_tests: int
    diagnostics: List[str]
    error_details: Optional[str] = None
    execution_time: float
    requires_manual_config: Optional[bool] = False
    static_analysis_fallback: Optional['TestSpriteResult'] = None

class GeminiAnalysis(BaseModel):
    issue_summary: str
    bugs_detected: List[str]
    optimizations: List[str]
    patch: str
    deployable_status: DeployableStatus
    confidence_score: float

class Job(BaseModel):
    id: str
    repository_id: int
    commit_sha: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    
    # Analysis results
    commit: Optional[Commit] = None
    testsprite_result: Optional[TestSpriteResult] = None
    gemini_analysis: Optional[GeminiAnalysis] = None
    
    # GitHub operations
    branch_name: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None

class JobCreate(BaseModel):
    repository_id: int
    commit_sha: str

class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    testsprite_result: Optional[TestSpriteResult] = None
    gemini_analysis: Optional[GeminiAnalysis] = None
    branch_name: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None

class WebhookPayload(BaseModel):
    ref: str
    repository: Dict[str, Any]
    commits: List[Dict[str, Any]]
    after: str
    before: str
    pusher: Dict[str, Any]

class OAuthToken(BaseModel):
    access_token: str
    token_type: str
    scope: str
    user_id: int

class GitHubOAuthResponse(BaseModel):
    access_token: str
    token_type: str
    scope: str