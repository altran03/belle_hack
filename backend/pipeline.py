import os
import uuid
import tempfile
import shutil
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models.schemas import JobCreate, JobStatus, DeployableStatus
from models.database import Job, Repository, User
from github_ops import GitHubOperations
from testsprite_client import TestSpriteClient
from gemini_client import GeminiClient
from utils.prompt_builders import PromptBuilder
from utils.patch_applier import PatchApplier

class AnalysisPipeline:
    def __init__(self):
        self.testsprite_client = TestSpriteClient()
        self.gemini_client = GeminiClient()
        self.prompt_builder = PromptBuilder()
        self.patch_applier = PatchApplier()
    
    async def run_analysis(self, job_data: JobCreate, repository: Repository, db: Session):
        """Initialize job and prepare for analysis - wait for TestSprite configuration"""
        job_id = str(uuid.uuid4())
        
        # Create job record
        job = Job(
            id=job_id,
            repository_id=job_data.repository_id,
            user_id=repository.owner_id,
            commit_sha=job_data.commit_sha,
            status=JobStatus.PENDING
        )
        
        db.add(job)
        db.commit()
        
        temp_workspace = None
        
        try:
            # Update status to analyzing
            job.status = JobStatus.ANALYZING
            db.commit()
            
            # Get user's access token
            user = db.query(User).filter(User.id == repository.owner_id).first()
            if not user or not user.access_token:
                raise Exception("User access token not found")
            
            github_ops = GitHubOperations(user.access_token)
            
            # Extract owner and repo from full_name
            owner, repo_name = repository.full_name.split("/", 1)
            
            # Fetch commit details
            commit_details = await github_ops.get_commit_details(owner, repo_name, job_data.commit_sha)
            
            # Update job with commit details
            job.commit_message = commit_details["commit"]["message"]
            job.commit_author = commit_details["commit"]["author"]["name"]
            job.commit_author_email = commit_details["commit"]["author"]["email"]
            job.commit_timestamp = datetime.fromisoformat(
                commit_details["commit"]["author"]["date"].replace("Z", "+00:00")
            )
            job.commit_url = commit_details["html_url"]
            
            # Download commit zipball
            temp_workspace = await github_ops.fetch_commit_zipball(
                owner, repo_name, job_data.commit_sha
            )
            
            # Store the workspace path for later use (temporarily in error_details)
            job.testsprite_error_details = temp_workspace
            
            # Set initial TestSprite status - analysis running
            job.testsprite_passed = False
            job.testsprite_total_tests = 0
            job.testsprite_failed_tests = 0
            job.testsprite_diagnostics = json.dumps(["TestSprite analysis running..."])
            job.testsprite_execution_time = 0.0
            
            # Update status to testing
            job.status = JobStatus.TESTING
            job.updated_at = datetime.utcnow()
            db.commit()
            
            print(f"Job {job_id} initialized, starting TestSprite analysis...")
            
            # Start both TestSprite and Gemini analysis in background (non-blocking)
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            # Use ThreadPoolExecutor to run both analyses in separate threads
            executor = ThreadPoolExecutor(max_workers=2)
            executor.submit(self._run_testsprite_sync, job_id, temp_workspace)
            executor.submit(self._run_gemini_sync, job_id, temp_workspace, job.commit_sha, job.commit_message)
            
        except Exception as e:
            # Update job status to failed
            job.status = JobStatus.FAILED
            job.testsprite_error_details = str(e)
            job.updated_at = datetime.utcnow()
            db.commit()
            
            print(f"Job initialization failed for job {job_id}: {e}")
            
        # Note: We don't cleanup the workspace here - we need it for later analysis

    def _run_testsprite_sync(self, job_id: str, temp_workspace: str):
        """Run TestSprite analysis in a separate thread without blocking the main thread"""
        import asyncio
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            print(f"Starting background TestSprite analysis for job {job_id}")
            
            # Run TestSprite analysis
            testsprite_result = loop.run_until_complete(
                self.testsprite_client.run_testsprite_after_config(temp_workspace)
            )
            
            # Update job with results (create new DB session for thread)
            from models.database import get_db
            db = next(get_db())
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    # Update job with TestSprite results
                    job.testsprite_passed = testsprite_result.get("passed", False)
                    job.testsprite_total_tests = testsprite_result.get("total_tests", 0)
                    job.testsprite_failed_tests = testsprite_result.get("failed_tests", 0)
                    job.testsprite_diagnostics = json.dumps(testsprite_result.get("diagnostics", []))
                    job.testsprite_error_details = testsprite_result.get("error_details")
                    job.testsprite_execution_time = testsprite_result.get("execution_time", 0.0)
                    job.updated_at = datetime.utcnow()
                    db.commit()
                    
                    print(f"TestSprite analysis completed for job {job_id}")
                else:
                    print(f"Job {job_id} not found for TestSprite update")
            finally:
                db.close()
                
        except Exception as e:
            print(f"Background TestSprite analysis failed for job {job_id}: {e}")
            # Update job with error
            from models.database import get_db
            db = next(get_db())
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.testsprite_diagnostics = json.dumps([f"TestSprite analysis failed: {str(e)}"])
                    job.testsprite_error_details = str(e)
                    job.updated_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
        finally:
            # Cleanup temporary workspace after analysis
            if temp_workspace and os.path.exists(temp_workspace):
                shutil.rmtree(os.path.dirname(temp_workspace), ignore_errors=True)
                print(f"Cleaned up workspace for job {job_id}")
            
            # Close the event loop
            loop.close()

    def _run_gemini_sync(self, job_id: str, temp_workspace: str, commit_sha: str, commit_message: str):
        """Run Gemini analysis independently in a separate thread"""
        import asyncio
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            print(f"Starting independent Gemini analysis for job {job_id}")
            
            # Run Gemini analysis independently
            gemini_analysis = loop.run_until_complete(
                self.gemini_client.analyze_code_and_generate_patch(
                    temp_workspace,
                    commit_sha,
                    commit_message,
                    None  # No TestSprite results needed
                )
            )
            
            # Update job with Gemini results (create new DB session for thread)
            from models.database import get_db
            db = next(get_db())
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    # Update job with Gemini results
                    job.gemini_issue_summary = gemini_analysis.get("issue_summary", "")
                    job.gemini_bugs_detected = json.dumps(gemini_analysis.get("bugs_detected", []))
                    job.gemini_optimizations = json.dumps(gemini_analysis.get("optimizations", []))
                    job.gemini_patch = gemini_analysis.get("patch", "")
                    job.gemini_deployable_status = gemini_analysis.get("deployable_status", "unknown")
                    job.gemini_confidence_score = gemini_analysis.get("confidence_score", 0.0)
                    job.updated_at = datetime.utcnow()
                    db.commit()
                    
                    print(f"Independent Gemini analysis completed for job {job_id}")
                else:
                    print(f"Job {job_id} not found for Gemini update")
            finally:
                db.close()
                
        except Exception as e:
            print(f"Independent Gemini analysis failed for job {job_id}: {e}")
            # Update job with error
            from models.database import get_db
            db = next(get_db())
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.gemini_issue_summary = f"Analysis failed: {str(e)}"
                    job.gemini_bugs_detected = json.dumps([])
                    job.gemini_optimizations = json.dumps([])
                    job.gemini_patch = ""
                    job.gemini_deployable_status = "unknown"
                    job.gemini_confidence_score = 0.0
                    job.updated_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
        finally:
            # Close the event loop
            loop.close()
    
    async def run_full_analysis(self, job_id: str, db: Session):
        """Run the complete analysis pipeline after TestSprite configuration"""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise Exception("Job not found")
        
        # Get the workspace path from error_details (temporarily stored there)
        temp_workspace = job.testsprite_error_details
        
        try:
            # Update status to testing
            job.status = JobStatus.TESTING
            db.commit()
            
            # Run TestSprite analysis
            testsprite_result = await self.testsprite_client.run_testsprite_after_config(temp_workspace)
            
            # Update job with TestSprite results
            job.testsprite_passed = testsprite_result["passed"]
            job.testsprite_total_tests = testsprite_result["total_tests"]
            job.testsprite_failed_tests = testsprite_result["failed_tests"]
            job.testsprite_diagnostics = str(testsprite_result["diagnostics"])
            job.testsprite_error_details = testsprite_result.get("error_details")
            job.testsprite_execution_time = testsprite_result["execution_time"]
            
            # Update status to fixing
            job.status = JobStatus.FIXING
            db.commit()
            
            # Run Gemini analysis
            gemini_analysis = await self.gemini_client.analyze_code_and_generate_patch(
                temp_workspace,
                job.commit_sha,
                job.commit_message,
                testsprite_result
            )
            
            # Update job with Gemini results
            job.gemini_issue_summary = gemini_analysis["issue_summary"]
            job.gemini_bugs_detected = str(gemini_analysis["bugs_detected"])
            job.gemini_optimizations = str(gemini_analysis["optimizations"])
            job.gemini_patch = gemini_analysis["patch"]
            job.gemini_deployable_status = gemini_analysis["deployable_status"]
            job.gemini_confidence_score = gemini_analysis["confidence_score"]
            
            # Test the patch if one was generated
            if gemini_analysis["patch"]:
                patch_test_result = await self.testsprite_client.run_tests_with_patch(
                    temp_workspace, gemini_analysis["patch"]
                )
                
                # Update diagnostics with patch test results
                if patch_test_result["passed"]:
                    job.testsprite_diagnostics += f"\nPatch validation: PASSED"
                else:
                    job.testsprite_diagnostics += f"\nPatch validation: FAILED - {patch_test_result['diagnostics']}"
            
            # Update status to ready for review
            job.status = JobStatus.READY_FOR_REVIEW
            job.updated_at = datetime.utcnow()
            db.commit()
            
            print(f"Full analysis completed for job {job_id}")
            
        except Exception as e:
            # Update job status to failed
            job.status = JobStatus.FAILED
            job.testsprite_error_details = str(e)
            job.updated_at = datetime.utcnow()
            db.commit()
            
            print(f"Full analysis failed for job {job_id}: {e}")
            
        finally:
            # Cleanup temporary workspace
            if temp_workspace and os.path.exists(temp_workspace):
                shutil.rmtree(os.path.dirname(temp_workspace), ignore_errors=True)
    
    async def approve_and_create_pr(self, job_id: str, db: Session) -> Dict[str, Any]:
        """Approve the job and create a pull request"""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise Exception("Job not found")
        
        if job.status != JobStatus.READY_FOR_REVIEW:
            raise Exception("Job is not ready for approval")
        
        try:
            # Get repository and user
            repository = db.query(Repository).filter(Repository.id == job.repository_id).first()
            user = db.query(User).filter(User.id == job.user_id).first()
            
            if not repository or not user or not user.access_token:
                raise Exception("Repository or user not found")
            
            github_ops = GitHubOperations(user.access_token)
            
            # Extract owner and repo
            owner, repo_name = repository.full_name.split("/", 1)
            
            # Generate branch name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            branch_name = f"bugsniper/fix-{timestamp}"
            
            # Get default branch
            default_branch = await github_ops.get_default_branch(owner, repo_name)
            
            # Create branch
            await github_ops.create_branch(owner, repo_name, branch_name, job.commit_sha)
            
            # Commit and push patch
            commit_message = f"BugSniper Pro: Fix issues in {job.commit_sha[:8]}\n\n{job.gemini_issue_summary}"
            
            success = await github_ops.commit_and_push_patch(
                owner, repo_name, branch_name, job.gemini_patch, commit_message
            )
            
            if not success:
                raise Exception("Failed to commit and push patch")
            
            # Create pull request
            pr_title = f"BugSniper Pro: Fix issues in {job.commit_sha[:8]}"
            pr_body = f"""
## BugSniper Pro Analysis Results

**Commit:** {job.commit_sha}  
**Author:** {job.commit_author}  
**Message:** {job.commit_message}

### Issues Detected
{chr(10).join(f"- {bug}" for bug in eval(job.gemini_bugs_detected))}

### Optimizations
{chr(10).join(f"- {opt}" for opt in eval(job.gemini_optimizations))}

### TestSprite Results
- **Status:** {'✅ PASSED' if job.testsprite_passed else '❌ FAILED'}
- **Tests:** {job.testsprite_total_tests} total, {job.testsprite_failed_tests} failed
- **Confidence:** {job.gemini_confidence_score:.2f}

### Deployable Status
{'🟢 DEPLOYABLE' if job.gemini_deployable_status == 'deployable' else '🔴 NOT DEPLOYABLE' if job.gemini_deployable_status == 'not_deployable' else '🟡 UNKNOWN'}

---
*This PR was automatically generated by BugSniper Pro*
"""
            
            pr_result = await github_ops.create_pull_request(
                owner, repo_name, pr_title, pr_body, branch_name, default_branch
            )
            
            if pr_result:
                # Update job with PR information
                job.status = JobStatus.COMPLETED
                job.branch_name = branch_name
                job.pr_url = pr_result["html_url"]
                job.pr_number = pr_result["number"]
                job.updated_at = datetime.utcnow()
                db.commit()
                
                return {
                    "success": True,
                    "pr_url": pr_result["html_url"],
                    "pr_number": pr_result["number"],
                    "branch_name": branch_name
                }
            else:
                raise Exception("Failed to create pull request")
                
        except Exception as e:
            job.status = JobStatus.FAILED
            job.testsprite_error_details = str(e)
            job.updated_at = datetime.utcnow()
            db.commit()
            
            return {
                "success": False,
                "error": str(e)
            }