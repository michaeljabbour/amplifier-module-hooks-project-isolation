"""
amplifier-module-hooks-project-isolation

Per-project session storage for Amplifier CLI applications.
Automatically isolates sessions by project (git root or CWD).
"""

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from amplifier_core.models import HookResult

__version__ = "1.0.0"
__amplifier_module_type__ = "hook"


async def mount(coordinator, config: dict):
    """
    Mount function that registers the project isolation hook.

    Args:
        coordinator: Amplifier ModuleCoordinator instance
        config: Configuration dictionary with keys:
            - use_git_root: bool (default: True)
            - storage_base: str (default: ~/.amplifier/projects)
            - create_dirs: bool (default: True)
    """
    # Extract configuration
    use_git_root = config.get("use_git_root", True)
    storage_base = Path(config.get("storage_base", "~/.amplifier/projects")).expanduser()
    create_dirs = config.get("create_dirs", True)

    # Create handler
    handler = _ProjectIsolationHandler(
        use_git_root=use_git_root,
        storage_base=storage_base,
        create_dirs=create_dirs
    )

    # Register hook for session start
    coordinator.hooks.register("session:start", handler.on_session_start)


class _ProjectIsolationHandler:
    """Internal handler for project isolation logic."""

    def __init__(self, use_git_root: bool, storage_base: Path, create_dirs: bool):
        """
        Initialize the project isolation handler.

        Args:
            use_git_root: Whether to use git root for project detection
            storage_base: Base directory for project storage
            create_dirs: Whether to auto-create directories
        """
        self.use_git_root = use_git_root
        self.storage_base = storage_base
        self.create_dirs = create_dirs

    async def on_session_start(self, event: str, context: dict) -> HookResult:
        """
        Hook handler called when a session starts.

        Detects the current project and sets the storage path accordingly.
        Creates collision-proof storage with metadata and indexing.
        Modifies context in place and returns HookResult.

        Args:
            event: Event name (always "session:start")
            context: Session context dictionary (modified in place)

        Returns:
            HookResult with action="continue"
        """
        # Detect project root
        project_root = self._detect_project_root()

        # Generate readable slug
        project_slug = self._generate_slug(project_root.name)

        # Generate collision-proof hash from full path
        path_hash = self._generate_path_hash(str(project_root))

        # Build collision-proof project directory name
        project_dir_name = f"{project_slug}-{path_hash}"
        project_dir = self.storage_base / project_dir_name

        # Build storage path
        storage_path = project_dir / "sessions"

        # Create directories if configured
        if self.create_dirs:
            storage_path.mkdir(parents=True, exist_ok=True)

            # Store/update project metadata
            self._update_project_metadata(project_dir, project_root, context)

            # Update project index
            self._update_project_index(project_dir, context)

        # Set storage path in context (modified in place)
        context["storage_path"] = str(storage_path)
        context["project_root"] = str(project_root)
        context["project_slug"] = project_slug
        context["project_dir_name"] = project_dir_name

        # Return success
        return HookResult(action="continue")

    def _detect_project_root(self) -> Path:
        """
        Detect the project root directory.

        Returns:
            Path to project root (git root or CWD)
        """
        if self.use_git_root:
            git_root = self._get_git_root()
            if git_root:
                return git_root

        # Fallback to current working directory
        return Path.cwd()

    def _get_git_root(self) -> Optional[Path]:
        """
        Get the git repository root path.

        Returns:
            Path to git root, or None if not in a git repository
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
                cwd=os.getcwd()
            )
            return Path(result.stdout.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _generate_slug(self, name: str) -> str:
        """
        Generate a URL-safe slug from a project name.

        Args:
            name: Project directory name

        Returns:
            URL-safe slug (lowercase, alphanumeric + hyphens)
        """
        # Convert to lowercase
        slug = name.lower()

        # Replace spaces and underscores with hyphens
        slug = re.sub(r'[\s_]+', '-', slug)

        # Remove all non-alphanumeric characters except hyphens
        slug = re.sub(r'[^a-z0-9-]', '', slug)

        # Remove duplicate hyphens
        slug = re.sub(r'-+', '-', slug)

        # Strip leading/trailing hyphens
        slug = slug.strip('-')

        # Ensure non-empty
        if not slug:
            slug = "default"

        return slug

    def _generate_path_hash(self, path: str) -> str:
        """
        Generate a short hash from the full project path for collision-proofing.

        Args:
            path: Full absolute path to the project

        Returns:
            First 6 characters of SHA-256 hash (hex)
        """
        # Hash the full path
        hash_obj = hashlib.sha256(path.encode('utf-8'))

        # Return first 6 characters for readability
        return hash_obj.hexdigest()[:6]

    def _update_project_metadata(self, project_dir: Path, project_root: Path, context: dict) -> None:
        """
        Store/update project metadata in the project directory.

        Creates or updates metadata.json with project information including
        full path, git repository details, and access timestamps.

        Args:
            project_dir: Directory where metadata should be stored
            project_root: Root directory of the project
            context: Session context (may contain additional metadata)
        """
        metadata_file = project_dir / "metadata.json"

        # Get git information if available
        git_remote = self._get_git_remote()
        git_branch = self._get_git_branch()

        # Load existing metadata or create new
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "first_seen": datetime.now().isoformat(),
                "slug": self._generate_slug(project_root.name)
            }

        # Update metadata
        metadata.update({
            "full_path": str(project_root),
            "git_remote": git_remote,
            "git_branch": git_branch,
            "last_accessed": datetime.now().isoformat(),
            "purpose": context.get("purpose", "Amplifier CLI session")
        })

        # Write metadata
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _update_project_index(self, project_dir: Path, context: dict) -> None:
        """
        Maintain an index of all sessions in this project.

        Creates or updates index.json with a list of all sessions,
        their timestamps, and metadata.

        Args:
            project_dir: Directory where index should be stored
            context: Session context containing session_id and other metadata
        """
        index_file = project_dir / "index.json"

        # Load existing index or create new
        if index_file.exists():
            with open(index_file, 'r') as f:
                index = json.load(f)
        else:
            index = {
                "sessions": []
            }

        # Create session record
        session_record = {
            "session_id": context.get("session_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "message_count": context.get("message_count", 0)
        }

        # Append new session
        index["sessions"].append(session_record)

        # Sort by timestamp (most recent first)
        index["sessions"].sort(key=lambda s: s["timestamp"], reverse=True)

        # Write index
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

    def _get_git_remote(self) -> Optional[str]:
        """
        Get the git remote URL.

        Returns:
            Remote URL string, or None if not in a git repository
        """
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
                cwd=os.getcwd()
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _get_git_branch(self) -> Optional[str]:
        """
        Get the current git branch name.

        Returns:
            Branch name string, or None if not in a git repository
        """
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
                cwd=os.getcwd()
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None
