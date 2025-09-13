import os
import tempfile
import zipfile
import subprocess
import json
from typing import Optional, Dict, Any, List
import httpx
from git import Repo
import shutil
from datetime import datetime

class GitHubOperations:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "BugSniper-Pro/1.0"
        }
    
    async def fetch_commit_zipball(self, owner: str, repo: str, commit_sha: str) -> str:
        """Download commit zipball and return path to extracted directory"""
        url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{commit_sha}"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="bugsniper_")
            zip_path = os.path.join(temp_dir, "commit.zip")
            
            # Save zip file
            with open(zip_path, "wb") as f:
                f.write(response.content)
            
            # Extract zip file
            extract_dir = os.path.join(temp_dir, "extracted")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find the actual repo directory (GitHub adds a prefix)
            extracted_items = os.listdir(extract_dir)
            if extracted_items:
                repo_dir = os.path.join(extract_dir, extracted_items[0])
                return repo_dir
            
            raise Exception("Failed to extract commit zipball")
    
    async def get_commit_details(self, owner: str, repo: str, commit_sha: str) -> Dict[str, Any]:
        """Get detailed commit information"""
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch of the repository"""
        repo_info = await self.get_repository_info(owner, repo)
        return repo_info.get("default_branch", "main")
    
    async def create_branch(self, owner: str, repo: str, branch_name: str, base_sha: str) -> bool:
        """Create a new branch from a specific commit"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
        
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        }
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(url, headers=self.headers, json=data)
            return response.status_code == 201
    
    async def commit_and_push_patch(self, owner: str, repo: str, branch_name: str, 
                                   patch_content: str, commit_message: str) -> bool:
        """Clone repo, apply patch, commit and push"""
        temp_dir = tempfile.mkdtemp(prefix="bugsniper_push_")
        
        try:
            # Clone repository
            clone_url = f"https://{self.access_token}@github.com/{owner}/{repo}.git"
            repo_path = os.path.join(temp_dir, repo)
            
            repo_obj = Repo.clone_from(clone_url, repo_path)
            
            # Checkout the branch
            repo_obj.git.checkout(branch_name)
            
            # Apply patch
            patch_file = os.path.join(temp_dir, "patch.diff")
            with open(patch_file, "w") as f:
                f.write(patch_content)
            
            # Apply patch using git
            try:
                repo_obj.git.apply(patch_file)
            except Exception as e:
                print(f"Failed to apply patch: {e}")
                return False
            
            # Add all changes
            repo_obj.git.add(".")
            
            # Commit
            repo_obj.index.commit(commit_message)
            
            # Push
            origin = repo_obj.remote("origin")
            origin.push(branch_name)
            
            return True
            
        except Exception as e:
            print(f"Error in commit_and_push_patch: {e}")
            return False
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def create_pull_request(self, owner: str, repo: str, title: str, 
                                 body: str, head_branch: str, base_branch: str) -> Optional[Dict[str, Any]]:
        """Create a pull request"""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(url, headers=self.headers, json=data)
            
            if response.status_code == 201:
                return response.json()
            else:
                print(f"Failed to create PR: {response.status_code} - {response.text}")
                return None
    
    async def setup_webhook(self, owner: str, repo: str, webhook_url: str, 
                           webhook_secret: str) -> Optional[Dict[str, Any]]:
        """Set up a webhook for the repository"""
        url = f"https://api.github.com/repos/{owner}/{repo}/hooks"
        
        data = {
            "name": "web",
            "active": True,
            "events": ["push"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": webhook_secret
            }
        }
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(url, headers=self.headers, json=data)
            
            if response.status_code == 201:
                return response.json()
            else:
                print(f"Failed to create webhook: {response.status_code} - {response.text}")
                return None
    
    async def get_user_repositories(self, username: str = None) -> List[Dict[str, Any]]:
        """Get user's repositories (authenticated user's repos)"""
        # Use the authenticated user endpoint instead of public user endpoint
        url = "https://api.github.com/user/repos"
        
        # Add query parameters for better results
        params = {
            "type": "all",  # Get all repos (public, private, forks)
            "sort": "updated",
            "per_page": 100
        }
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers, params=params)
            
            if response.status_code == 401:
                raise Exception("Invalid or expired access token")
            elif response.status_code == 403:
                raise Exception("Access token lacks required permissions")
            
            response.raise_for_status()
            return response.json()
    
    async def delete_webhook(self, owner: str, repo: str, webhook_id: int) -> bool:
        """Delete a webhook from the repository"""
        url = f"https://api.github.com/repos/{owner}/{repo}/hooks/{webhook_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=self.headers)
            
            if response.status_code == 204:
                return True
            else:
                print(f"Failed to delete webhook: {response.status_code} - {response.text}")
                return False
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information"""
        url = "https://api.github.com/user"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()