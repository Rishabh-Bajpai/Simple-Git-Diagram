import requests
import os
from typing import Optional, List, Tuple

import logging

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self, pat: Optional[str] = None):
        # Prioritize passed PAT, then env PAT
        self.pat = pat or os.getenv("GITHUB_PAT")
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.pat:
            self.headers["Authorization"] = f"token {self.pat}"
            logger.info("GitHubService initialized with PAT")
        else:
            logger.warning("GitHubService initialized WITHOUT PAT (Rate limits will be low)")

    def get_default_branch(self, username: str, repo: str) -> str:
        url = f"https://api.github.com/repos/{username}/{repo}"
        logger.debug(f"Fetching default branch from: {url}")
        resp = requests.get(url, headers=self.headers)
        logger.debug(f"Default branch response status: {resp.status_code}")
        
        if resp.status_code == 200:
            branch = resp.json().get("default_branch", "main")
            logger.info(f"Default branch for {username}/{repo} is '{branch}'")
            return branch
        if resp.status_code == 404:
            logger.error(f"Repository not found: {username}/{repo}")
            raise ValueError("Repository not found (or private and no valid PAT provided).")
        
        logger.error(f"GitHub API Error for {username}/{repo}: {resp.status_code}")
        raise Exception(f"GitHub API Error: {resp.status_code}")

    def get_file_tree(self, username: str, repo: str) -> Tuple[str, str]:
        branch = self.get_default_branch(username, repo)
        url = f"https://api.github.com/repos/{username}/{repo}/git/trees/{branch}?recursive=1"
        logger.debug(f"Fetching file tree from: {url}")
        resp = requests.get(url, headers=self.headers)
        
        if resp.status_code != 200:
            logger.error(f"Failed to fetch file tree. Status: {resp.status_code}")
            raise Exception(f"Failed to fetch file tree: {resp.status_code}")
            
        data = resp.json()
        if "tree" not in data:
            logger.warning("No 'tree' found in response data")
            return ""

        files = []
        MAX_FILES = 80 # Limit to prevent context overflow for local LLMs
        for item in data["tree"]:
            if len(files) >= MAX_FILES:
                logger.warning(f"File limit ({MAX_FILES}) reached. Truncating tree.")
                files.append(f"... (truncated, {len(data['tree']) - MAX_FILES} more files) ...")
                break
                
            path = item["path"]
            if self._should_include(path):
                files.append(path)
        
        logger.info(f"Found {len(files)} files in repository")
        return "\n".join(files), branch # Return tuple

    def get_readme(self, username: str, repo: str) -> str:
        url = f"https://api.github.com/repos/{username}/{repo}/readme"
        logger.debug(f"Fetching README from: {url}")
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            download_url = resp.json().get("download_url")
            if download_url:
                logger.debug(f"Downloading README content from: {download_url}")
                content_resp = requests.get(download_url)
                logger.info("README fetched successfully")
                content = content_resp.text
                # Truncate README if too long (e.g. > 15000 chars)
                if len(content) > 15000:
                    logger.warning("README too long, truncating to 15000 chars")
                    content = content[:15000] + "\n... (truncated) ..."
                return content
        
        logger.warning(f"README not found or inaccessible (Status: {resp.status_code})")
        return ""

    def _should_include(self, path: str) -> bool:
        excluded = [
            "node_modules/", "vendor/", "venv/", "__pycache__/", ".git/",
            ".jpg", ".png", ".gif", ".ico", ".svg", ".lock", ".min.js", ".map",
            ".css", ".scss", ".less", ".json", ".xml", ".yaml", ".yml", # detailed configs
            "test/", "tests/", "spec/", "docs/", "examples/" # non-essential folders
        ]
        path_lower = path.lower()
        return not any(ex in path_lower for ex in excluded)
