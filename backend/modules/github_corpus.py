"""
GitHub corpus integration module.

Handles downloading and caching corpus data from GitHub repositories.
Supports both git operations and GitHub API access.
"""

import os
import shutil
import tempfile
import subprocess
import requests
import zipfile
import tarfile
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import logging
import hashlib
import json
from datetime import datetime, timedelta

from backend.modules.path_validator import validate_repo_subpath

logger = logging.getLogger(__name__)


class GitHubCorpusManager:
    """Manages corpus downloads from GitHub repositories."""

    def __init__(self, cache_dir: str = ".corpus_cache"):
        """
        Initialize GitHub corpus manager.

        Args:
            cache_dir: Directory for caching downloaded repositories
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_metadata_file = self.cache_dir / "metadata.json"
        self.cache_metadata = self._load_cache_metadata()

    def fetch_corpus(
        self,
        repo_url: str,
        branch: str = "main",
        path: str = "",
        token: Optional[str] = None,
        force_refresh: bool = False
    ) -> Path:
        """
        Fetch corpus from GitHub repository.

        Args:
            repo_url: GitHub repository URL
            branch: Git branch to fetch
            path: Path within repository to corpus
            token: GitHub access token for private repos
            force_refresh: Force re-download even if cached

        Returns:
            Path to local corpus directory
        """
        # Parse repository information
        repo_info = self._parse_repo_url(repo_url)
        cache_key = self._get_cache_key(repo_info, branch)

        # Check cache
        if not force_refresh and self._is_cached(cache_key):
            logger.info(f"Using cached corpus for {repo_url}")
            return self._get_cache_path(cache_key, path)

        # Determine download method
        if self._has_git():
            local_path = self._fetch_with_git(repo_info, branch, token)
        else:
            local_path = self._fetch_with_api(repo_info, branch, token)

        # Update cache metadata
        self._update_cache_metadata(cache_key, repo_info, branch)

        # Return path to corpus within repository
        corpus_path = local_path / path if path else local_path
        if not corpus_path.exists():
            raise ValueError(f"Corpus path not found in repository: {path}")

        return corpus_path

    def _parse_repo_url(self, url: str) -> Dict[str, str]:
        """Parse GitHub repository URL to extract owner and repo name."""
        # Handle various URL formats
        if url.endswith('.git'):
            url = url[:-4]

        # Parse URL
        parsed = urlparse(url)

        if parsed.netloc in ['github.com', 'www.github.com']:
            # https://github.com/owner/repo format
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                return {
                    'owner': path_parts[0],
                    'repo': path_parts[1],
                    'host': parsed.netloc
                }
        elif not parsed.scheme:
            # Assume owner/repo format
            parts = url.split('/')
            if len(parts) == 2:
                return {
                    'owner': parts[0],
                    'repo': parts[1],
                    'host': 'github.com'
                }

        raise ValueError(f"Invalid GitHub repository URL: {url}")

    def _get_cache_key(self, repo_info: Dict[str, str], branch: str) -> str:
        """Generate cache key for repository."""
        key_string = f"{repo_info['owner']}/{repo_info['repo']}:{branch}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str, sub_path: str = "") -> Path:
        """
        Get path to cached repository with sub_path validation.

        Args:
            cache_key: The cache key identifying the repository
            sub_path: Optional subdirectory within the repository

        Returns:
            Path to the cached repository or subdirectory

        Raises:
            ValueError: If sub_path contains directory traversal attempts
        """
        repo_path = self.cache_dir / cache_key
        if sub_path:
            # Validate sub_path to prevent directory traversal
            validated_subpath = validate_repo_subpath(sub_path)
            if validated_subpath:
                full_path = repo_path / validated_subpath
                # Extra safety: ensure resolved path is within repo_path
                try:
                    full_path.resolve().relative_to(repo_path.resolve())
                except ValueError:
                    logger.warning(f"Sub-path escape attempt: {sub_path[:100]}")
                    raise ValueError("Invalid repository path: access denied")
                return full_path
        return repo_path

    def _is_cached(self, cache_key: str) -> bool:
        """Check if repository is cached and still valid."""
        if cache_key not in self.cache_metadata:
            return False

        cache_info = self.cache_metadata[cache_key]
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return False

        # Check cache age (default 7 days)
        cached_time = datetime.fromisoformat(cache_info['cached_at'])
        cache_ttl = timedelta(days=7)
        if datetime.now() - cached_time > cache_ttl:
            logger.info("Cache expired, will refresh")
            return False

        return True

    def _has_git(self) -> bool:
        """Check if git is available."""
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _fetch_with_git(
        self,
        repo_info: Dict[str, str],
        branch: str,
        token: Optional[str] = None
    ) -> Path:
        """Fetch repository using git clone with sparse checkout."""
        cache_key = self._get_cache_key(repo_info, branch)
        target_dir = self._get_cache_path(cache_key)

        # Clean existing directory if it exists
        if target_dir.exists():
            shutil.rmtree(target_dir)

        # Build clone URL
        if token:
            clone_url = f"https://{token}@{repo_info['host']}/{repo_info['owner']}/{repo_info['repo']}.git"
        else:
            clone_url = f"https://{repo_info['host']}/{repo_info['owner']}/{repo_info['repo']}.git"

        logger.info(f"Cloning repository with git: {repo_info['owner']}/{repo_info['repo']}")

        try:
            # Clone with depth=1 for efficiency
            subprocess.run(
                [
                    'git', 'clone',
                    '--depth', '1',
                    '--branch', branch,
                    '--single-branch',
                    clone_url,
                    str(target_dir)
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Remove .git directory to save space
            git_dir = target_dir / '.git'
            if git_dir.exists():
                shutil.rmtree(git_dir)

            logger.info(f"Successfully cloned repository to {target_dir}")
            return target_dir

        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr}")
            raise RuntimeError(f"Failed to clone repository: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Git clone timed out after 5 minutes")

    def _fetch_with_api(
        self,
        repo_info: Dict[str, str],
        branch: str,
        token: Optional[str] = None
    ) -> Path:
        """Fetch repository using GitHub API."""
        cache_key = self._get_cache_key(repo_info, branch)
        target_dir = self._get_cache_path(cache_key)

        # Clean existing directory if it exists
        if target_dir.exists():
            shutil.rmtree(target_dir)

        # Build API URL for archive
        archive_url = (
            f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}"
            f"/zipball/{branch}"
        )

        headers = {}
        if token:
            headers['Authorization'] = f'token {token}'
        headers['Accept'] = 'application/vnd.github.v3+json'

        logger.info(f"Downloading repository via API: {repo_info['owner']}/{repo_info['repo']}")

        try:
            # Download archive
            response = requests.get(archive_url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name

            # Extract archive
            target_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                # Extract all files
                zip_ref.extractall(target_dir)

                # GitHub creates a top-level directory like owner-repo-hash
                # Move contents up one level
                extracted_dirs = list(target_dir.iterdir())
                if len(extracted_dirs) == 1 and extracted_dirs[0].is_dir():
                    temp_dir = target_dir / '_temp_extract'
                    shutil.move(str(extracted_dirs[0]), str(temp_dir))

                    # Move all contents from temp dir to target
                    for item in temp_dir.iterdir():
                        shutil.move(str(item), str(target_dir / item.name))

                    # Remove temp directory
                    temp_dir.rmdir()

            # Clean up temporary file
            os.unlink(tmp_path)

            logger.info(f"Successfully downloaded repository to {target_dir}")
            return target_dir

        except requests.RequestException as e:
            logger.error(f"Failed to download repository: {e}")
            raise RuntimeError(f"Failed to download repository: {e}")

    def _load_cache_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from disk."""
        if self.cache_metadata_file.exists():
            try:
                with open(self.cache_metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Failed to load cache metadata, starting fresh")
        return {}

    def _update_cache_metadata(
        self,
        cache_key: str,
        repo_info: Dict[str, str],
        branch: str
    ) -> None:
        """Update cache metadata."""
        self.cache_metadata[cache_key] = {
            'owner': repo_info['owner'],
            'repo': repo_info['repo'],
            'branch': branch,
            'cached_at': datetime.now().isoformat(),
            'cache_dir': str(self._get_cache_path(cache_key))
        }

        try:
            with open(self.cache_metadata_file, 'w') as f:
                json.dump(self.cache_metadata, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear cached repositories.

        Args:
            older_than_days: Only clear caches older than this many days

        Returns:
            Number of cache entries cleared
        """
        cleared = 0

        for cache_key, cache_info in list(self.cache_metadata.items()):
            should_clear = True

            if older_than_days is not None:
                cached_time = datetime.fromisoformat(cache_info['cached_at'])
                age = datetime.now() - cached_time
                should_clear = age.days > older_than_days

            if should_clear:
                cache_path = self._get_cache_path(cache_key)
                if cache_path.exists():
                    shutil.rmtree(cache_path)
                    logger.info(f"Cleared cache for {cache_info['owner']}/{cache_info['repo']}")
                del self.cache_metadata[cache_key]
                cleared += 1

        # Save updated metadata
        if cleared > 0:
            try:
                with open(self.cache_metadata_file, 'w') as f:
                    json.dump(self.cache_metadata, f, indent=2)
            except IOError as e:
                logger.error(f"Failed to save cache metadata: {e}")

        return cleared

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached repositories."""
        info = {
            'cache_dir': str(self.cache_dir),
            'total_cached': len(self.cache_metadata),
            'total_size_mb': 0,
            'repositories': []
        }

        for cache_key, cache_data in self.cache_metadata.items():
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                # Calculate size
                size_bytes = sum(
                    f.stat().st_size
                    for f in cache_path.rglob('*')
                    if f.is_file()
                )
                size_mb = size_bytes / 1024 / 1024

                info['total_size_mb'] += size_mb
                info['repositories'].append({
                    **cache_data,
                    'size_mb': round(size_mb, 2),
                    'exists': True
                })
            else:
                info['repositories'].append({
                    **cache_data,
                    'size_mb': 0,
                    'exists': False
                })

        info['total_size_mb'] = round(info['total_size_mb'], 2)
        return info