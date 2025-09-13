from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
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

class PytestResult(BaseModel):
    passed: bool
    total_tests: int
    failed_tests: int
    diagnostics: List[str]
    error_details: Optional[str] = None
    execution_time: float

class BugDetected(BaseModel):
    type: str
    severity: str
    file: str
    line: int
    description: str
    impact: str
    reproduction: str

class Optimization(BaseModel):
    type: str
    file: str
    line: int
    current_approach: str
    suggested_approach: str
    benefit: str

class GeminiAnalysis(BaseModel):
    issue_summary: str
    bugs_detected: List[Union[BugDetected, str]]  # Support both object and string formats
    optimizations: List[Union[Optimization, str]]  # Support both object and string formats
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
    
    # Commit details
    commit_message: Optional[str] = None
    commit_author: Optional[str] = None
    commit_author_email: Optional[str] = None
    commit_timestamp: Optional[datetime] = None
    commit_url: Optional[str] = None
    
    # Analysis results
    commit: Optional[Commit] = None
    pytest_result: Optional[PytestResult] = None
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
    pytest_result: Optional[PytestResult] = None
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

class MonitorRepositoryRequest(BaseModel):
    owner: str
    repo: str