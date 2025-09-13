import os
import subprocess
import tempfile
from typing import Optional, Dict, Any
import shutil

class PatchApplier:
    def __init__(self):
        pass
    
    def apply_patch(self, workspace_path: str, patch_content: str) -> Dict[str, Any]:
        """Apply a unified diff patch to the workspace"""
        try:
            # Create temporary patch file
            patch_file = os.path.join(workspace_path, "bugsniper_patch.diff")
            
            with open(patch_file, "w") as f:
                f.write(patch_content)
            
            # Apply patch using git
            result = subprocess.run(
                ["git", "apply", "--check", patch_file],
                cwd=workspace_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Patch validation failed: {result.stderr}",
                    "details": result.stderr
                }
            
            # Actually apply the patch
            result = subprocess.run(
                ["git", "apply", patch_file],
                cwd=workspace_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to apply patch: {result.stderr}",
                    "details": result.stderr
                }
            
            # Clean up patch file
            os.remove(patch_file)
            
            return {
                "success": True,
                "message": "Patch applied successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during patch application: {str(e)}",
                "details": str(e)
            }
    
    def validate_patch(self, patch_content: str) -> Dict[str, Any]:
        """Validate a patch without applying it"""
        try:
            # Create temporary directory for validation
            temp_dir = tempfile.mkdtemp(prefix="patch_validation_")
            
            try:
                # Create a dummy file structure for validation
                patch_file = os.path.join(temp_dir, "patch.diff")
                
                with open(patch_file, "w") as f:
                    f.write(patch_content)
                
                # Try to parse the patch
                result = subprocess.run(
                    ["git", "apply", "--check", patch_file],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    return {
                        "valid": True,
                        "message": "Patch is valid"
                    }
                else:
                    return {
                        "valid": False,
                        "error": result.stderr,
                        "message": "Patch validation failed"
                    }
                    
            finally:
                # Cleanup
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "message": "Exception during patch validation"
            }
    
    def extract_patch_info(self, patch_content: str) -> Dict[str, Any]:
        """Extract information from a patch"""
        try:
            lines = patch_content.split('\n')
            files_modified = []
            additions = 0
            deletions = 0
            
            for line in lines:
                if line.startswith('--- a/') or line.startswith('+++ b/'):
                    file_path = line.split('/', 1)[1] if '/' in line else line[6:]
                    if file_path not in files_modified:
                        files_modified.append(file_path)
                elif line.startswith('+') and not line.startswith('+++'):
                    additions += 1
                elif line.startswith('-') and not line.startswith('---'):
                    deletions += 1
            
            return {
                "files_modified": files_modified,
                "additions": additions,
                "deletions": deletions,
                "total_changes": additions + deletions
            }
            
        except Exception as e:
            return {
                "files_modified": [],
                "additions": 0,
                "deletions": 0,
                "total_changes": 0,
                "error": str(e)
            }